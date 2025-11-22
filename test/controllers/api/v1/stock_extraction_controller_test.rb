require "test_helper"

# Ensure job class is loaded
ExtractStockPhotoJob

module Api
  module V1
    class StockExtractionControllerTest < ActionDispatch::IntegrationTest
      def setup
        # Ensure job class is loaded for status_key method
        ExtractStockPhotoJob

        # Use memory store for cache in tests (test env uses null_store by default)
        @original_cache_store = Rails.cache
        Rails.cache = ActiveSupport::Cache::MemoryStore.new

        @user = create(:user)
        @token = generate_jwt_token(@user)
        @image_blob = ActiveStorage::Blob.create_and_upload!(
          io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
          filename: "sample_image.jpg",
          content_type: "image/jpeg"
        )
        @analysis_results = {
          "name" => "Grey Hoodie",
          "category_name" => "Hoodies",
          "colors" => [ "grey" ],
          "gender_appropriate" => true,
          "confidence" => 0.9
        }
      end

      def teardown
        # Restore original cache store
        Rails.cache = @original_cache_store if @original_cache_store
      end

      test "extract requires authentication" do
        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: @analysis_results
          },
          as: :json

        assert_response :unauthorized
      end

      test "extract requires blob_id" do
        post "/api/v1/stock_extraction/extract",
          params: {
            analysis_results: @analysis_results
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :bad_request
        json = JSON.parse(response.body)
        assert_equal "MISSING_BLOB_ID", json["error"]["code"]
      end

      test "extract requires analysis_results" do
        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :bad_request
        json = JSON.parse(response.body)
        assert_equal "MISSING_ANALYSIS_RESULTS", json["error"]["code"]
      end

      test "extract rejects gender inappropriate items" do
        analysis_results = @analysis_results.merge("gender_appropriate" => false)

        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: analysis_results
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :unprocessable_entity
        json = JSON.parse(response.body)
        assert_equal "GENDER_MISMATCH", json["error"]["code"]
      end

      test "extract queues job successfully" do
        assert_enqueued_with(job: ExtractStockPhotoJob) do
          post "/api/v1/stock_extraction/extract",
            params: {
              blob_id: @image_blob.id,
              analysis_results: @analysis_results
            },
            headers: { "Authorization" => "Bearer #{@token}" },
            as: :json
        end

        assert_response :accepted
        json = JSON.parse(response.body)
        assert_equal true, json["success"]
        assert json["data"]["job_id"].present?
        assert_equal "processing", json["data"]["status"]
      end

      test "extract handles missing blob" do
        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: 999999,
            analysis_results: @analysis_results
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :not_found
        json = JSON.parse(response.body)
        assert_equal "BLOB_NOT_FOUND", json["error"]["code"]
      end

      test "extract handles invalid JSON in analysis_results" do
        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: "invalid json"
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :bad_request
        json = JSON.parse(response.body)
        assert_equal "INVALID_ANALYSIS_RESULTS", json["error"]["code"]
      end

      test "extract handles ArgumentError for invalid inventory item" do
        item = create(:inventory_item, user: create(:user)) # Different user's item

        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: @analysis_results,
            inventory_item_id: item.id
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :not_found # Controller returns :not_found for INVALID_INVENTORY_ITEM
        json = JSON.parse(response.body)
        assert_equal "INVALID_INVENTORY_ITEM", json["error"]["code"]
      end

      test "extract handles ArgumentError for empty analysis results" do
        # Empty hash {} is considered "present" in Rails, so we need to stub the service
        # to raise the error when it validates
        StockPhotoExtractionService.any_instance.stubs(:queue_extraction).raises(
          ArgumentError.new("Analysis results are required (at least one field must have a value)")
        )

        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: { "name" => "", "category_name" => nil } # Empty values that will fail validation
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :bad_request # Controller returns :bad_request for INVALID_ANALYSIS_RESULTS
        json = JSON.parse(response.body)
        assert_equal "INVALID_ANALYSIS_RESULTS", json["error"]["code"]
      end

      test "extract handles StandardError gracefully" do
        StockPhotoExtractionService.any_instance.stubs(:queue_extraction).raises(StandardError.new("Unexpected error"))

        post "/api/v1/stock_extraction/extract",
          params: {
            blob_id: @image_blob.id,
            analysis_results: @analysis_results
          },
          headers: { "Authorization" => "Bearer #{@token}" },
          as: :json

        assert_response :internal_server_error
        json = JSON.parse(response.body)
        assert_equal false, json["success"]
        assert_equal "EXTRACTION_ERROR", json["error"]["code"]
      end

      test "status handles StandardError gracefully" do
        ExtractStockPhotoJob.stubs(:get_status).raises(StandardError.new("Cache error"))

        get "/api/v1/stock_extraction/status/test-job-id",
          headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :internal_server_error
        json = JSON.parse(response.body)
        assert_equal false, json["success"]
        assert_equal "STATUS_ERROR", json["error"]["code"]
      end

      test "status requires authentication" do
        job_id = SecureRandom.uuid
        get "/api/v1/stock_extraction/status/#{job_id}"

        assert_response :unauthorized
      end

      test "status requires job_id" do
        get "/api/v1/stock_extraction/status/",
          headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :not_found
      end

      test "status returns job status" do
        job_id = SecureRandom.uuid

        # Create status in cache - ensure job class is loaded first
        ExtractStockPhotoJob
        status_key = ExtractStockPhotoJob.status_key(job_id)
        status_data = {
          "status" => "processing",
          "data" => nil,
          "error" => nil,
          "updated_at" => Time.current.iso8601
        }
        Rails.cache.write(status_key, status_data, expires_in: 1.hour)

        # Verify cache write worked
        cached = Rails.cache.read(status_key)
        assert_not_nil cached, "Cache write failed - status_data not found in cache"

        get "/api/v1/stock_extraction/status/#{job_id}",
          headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :ok
        json = JSON.parse(response.body)
        assert_equal true, json["success"]
        assert_equal "processing", json["data"]["status"]
      end

      test "status returns not_found for invalid job_id" do
        job_id = SecureRandom.uuid

        get "/api/v1/stock_extraction/status/#{job_id}",
          headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :ok
        json = JSON.parse(response.body)
        assert_equal "not_found", json["data"]["status"]
      end

      private

      def generate_jwt_token(user)
        payload = {
          user_id: user.id,
          exp: 1.hour.from_now.to_i
        }
        JWT.encode(payload, Rails.application.credentials.secret_key_base, "HS256")
      end
    end
  end
end
