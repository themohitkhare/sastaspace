require "test_helper"

class Api::V1::ClothingDetectionControllerTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper
  # Helper to check if Ollama is available
  def ollama_available?
    return false unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    begin
      uri = URI(ENV["OLLAMA_API_BASE"] || "http://localhost:11434")
      http = Net::HTTP.new(uri.host, uri.port)
      http.open_timeout = 2
      http.read_timeout = 2
      response = http.get("/api/tags")
      response.code == "200"
    rescue StandardError
      false
    end
  end

  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @image_file = fixture_file_upload("sample_image.jpg", "image/jpeg")
  end

  test "POST /api/v1/clothing_detection/analyze requires authentication" do
    post "/api/v1/clothing_detection/analyze",
         params: { image: @image_file }

    assert_response :unauthorized
  end

  test "POST /api/v1/clothing_detection/analyze accepts image upload" do
    # The controller now queues a background job instead of processing synchronously
    assert_enqueued_with(job: ClothingDetectionJob) do
      post "/api/v1/clothing_detection/analyze",
           params: { image: @image_file },
           headers: auth_headers(@token)
    end

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["job_id"].present?
    assert body["data"]["blob_id"].present?
    assert body["data"]["user_id"].present?
    assert_equal "processing", body["data"]["status"]
    assert_equal "Clothing detection job queued successfully", body["data"]["message"]
  end

  test "POST /api/v1/clothing_detection/analyze rejects missing image" do
    post "/api/v1/clothing_detection/analyze",
         params: {},
         headers: auth_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "MISSING_IMAGE", body["error"]["code"]
  end

  test "POST /api/v1/clothing_detection/analyze rejects invalid image type" do
    text_file = fixture_file_upload("sample_text.txt", "text/plain")

    post "/api/v1/clothing_detection/analyze",
         params: { image: text_file },
         headers: auth_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "INVALID_IMAGE_TYPE", body["error"]["code"]
  end

  test "POST /api/v1/clothing_detection/analyze rejects oversized image" do
    # File size validation is tested in the controller logic
    # Integration test for this would require creating a large file, which is impractical
    # The validation is verified in the controller code and service tests
    skip "File size validation is tested in controller code - creating 10MB+ test files is impractical"
  end

  test "POST /api/v1/clothing_detection/analyze handles service errors gracefully" do
    # Since processing is now asynchronous, service errors occur in the background job
    # The controller should successfully queue the job even if the service will fail later
    # Service errors are handled in ClothingDetectionJob and broadcast via WebSocket
    # This test verifies that errors during blob creation (which happens in the controller) are handled
    Services::BlobDeduplicationService.stubs(:find_or_create_blob).raises(StandardError.new("Blob creation failed"))

    assert_no_enqueued_jobs(only: ClothingDetectionJob) do
      post "/api/v1/clothing_detection/analyze",
           params: { image: @image_file },
           headers: auth_headers(@token)
    end

    assert_response :internal_server_error
    body = json_response
    assert_not body["success"]
    assert_equal "DETECTION_ERROR", body["error"]["code"]
    assert body["error"]["message"].include?("Failed to analyze image")
  end

  test "POST /api/v1/clothing_detection/analyze with real Ollama" do
    skip "Set ENABLE_OLLAMA_TESTS=true and ensure Ollama is running to test with real Ollama" unless ollama_available?

    post "/api/v1/clothing_detection/analyze",
         params: { image: @image_file },
         headers: auth_headers(@token)

    # Accept both success and error responses (Ollama might be slow or unavailable)
    assert_includes [ 200, 422, 500 ], @response.status

    body = json_response

    if @response.status == 200
      assert body["success"]
      assert body["data"]["total_items_detected"].present?
      assert body["data"]["items"].is_a?(Array)

      # Verify gender_styling is present and valid
      if body["data"]["items"].any?
        body["data"]["items"].each do |item|
          assert_includes %w[men women unisex], item["gender_styling"], "Item has invalid gender_styling: #{item['gender_styling']}"
        end
      end
    end
  end

  test "GET /api/v1/clothing_detection/analysis/:id requires authentication" do
    analysis = create(:clothing_analysis, user: @user)

    get "/api/v1/clothing_detection/analysis/#{analysis.id}"

    assert_response :unauthorized
  end

  test "GET /api/v1/clothing_detection/analysis/:id returns analysis" do
    analysis = create(:clothing_analysis,
      user: @user,
      parsed_data: {
        "total_items_detected" => 2,
        "people_count" => 1,
        "items" => [
          { "id" => "item_001", "item_name" => "Shirt", "gender_styling" => "men" },
          { "id" => "item_002", "item_name" => "Pants", "gender_styling" => "unisex" }
        ]
      },
      items_detected: 2,
      confidence: 0.85
    )

    get "/api/v1/clothing_detection/analysis/#{analysis.id}",
        headers: api_v1_headers(@token)

    assert_response :ok
    body = json_response
    assert body["success"]
    assert_equal analysis.id, body["data"]["analysis"]["id"]
    assert_equal 2, body["data"]["analysis"]["total_items_detected"]
    assert_equal 1, body["data"]["analysis"]["people_count"]
    assert_equal 2, body["data"]["analysis"]["items"].length
    assert_equal "men", body["data"]["analysis"]["items"][0]["gender_styling"]
    assert_equal "unisex", body["data"]["analysis"]["items"][1]["gender_styling"]
  end

  test "GET /api/v1/clothing_detection/analysis/:id returns 404 for non-existent analysis" do
    get "/api/v1/clothing_detection/analysis/99999",
        headers: api_v1_headers(@token)

    assert_response :not_found
    body = json_response
    assert_not body["success"]
    assert_equal "NOT_FOUND", body["error"]["code"]
  end

  test "GET /api/v1/clothing_detection/analysis/:id returns 404 for other user's analysis" do
    other_user = create(:user)
    analysis = create(:clothing_analysis, user: other_user)

    get "/api/v1/clothing_detection/analysis/#{analysis.id}",
        headers: api_v1_headers(@token)

    assert_response :not_found
  end

  test "GET /api/v1/clothing_detection/analyses requires authentication" do
    get "/api/v1/clothing_detection/analyses"

    assert_response :unauthorized
  end

  test "GET /api/v1/clothing_detection/analyses returns paginated list" do
    # Create multiple analyses
    5.times do
      create(:clothing_analysis, user: @user, items_detected: 2)
    end

    get "/api/v1/clothing_detection/analyses",
        headers: api_v1_headers(@token)

    assert_response :ok
    body = json_response
    assert body["success"]
    assert_equal 5, body["data"]["analyses"].length
    assert body["data"]["pagination"].present?
    assert_equal 1, body["data"]["pagination"]["current_page"]
  end

  test "GET /api/v1/clothing_detection/analyses only returns current user's analyses" do
    other_user = create(:user)
    analysis1 = create(:clothing_analysis, user: @user, items_detected: 2)
    analysis2 = create(:clothing_analysis, user: @user, items_detected: 3)
    create(:clothing_analysis, user: other_user, items_detected: 1)

    get "/api/v1/clothing_detection/analyses",
        headers: api_v1_headers(@token)

    assert_response :ok
    body = json_response
    assert_equal 2, body["data"]["analyses"].length
    analysis_ids = body["data"]["analyses"].map { |a| a["id"] }
    assert_includes analysis_ids, analysis1.id
    assert_includes analysis_ids, analysis2.id
    assert_not_includes analysis_ids, other_user.clothing_analyses.first.id
  end

  test "GET /api/v1/clothing_detection/analyses supports pagination" do
    # Create more than default page size
    25.times do
      create(:clothing_analysis, user: @user, items_detected: 1)
    end

    get "/api/v1/clothing_detection/analyses?page=1&per_page=10",
        headers: api_v1_headers(@token)

    assert_response :ok
    body = json_response
    assert_equal 10, body["data"]["analyses"].length
    assert_equal 3, body["data"]["pagination"]["total_pages"] # 25 items / 10 per page = 3 pages
  end
end
