require "test_helper"

class StockPhotoExtractionServiceTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper

  def setup
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @analysis_results = {
      "name" => "Blue Shirt",
      "category_name" => "Tops",
      "colors" => [ "blue" ],
      "gender_appropriate" => true,
      "confidence" => 0.9
    }
  end

  test "queue_extraction enqueues job successfully" do
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: @analysis_results
    )

    assert_enqueued_with(job: ExtractStockPhotoJob) do
      job_id = service.queue_extraction
      assert_not_nil job_id
    end
  end

  test "queue_extraction raises error when image_blob is missing" do
    service = StockPhotoExtractionService.new(
      image_blob: nil,
      user: @user,
      analysis_results: @analysis_results
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction raises error when user is missing" do
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: nil,
      analysis_results: @analysis_results
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction raises error when analysis_results is missing" do
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: nil
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction raises error when analysis_results is empty hash" do
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: {}
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction raises error when gender_appropriate is false" do
    analysis_results = @analysis_results.merge("gender_appropriate" => false)
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: analysis_results
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction validates inventory_item_id belongs to user" do
    other_user = create(:user)
    other_item = create(:inventory_item, user: other_user)

    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: @analysis_results,
      inventory_item_id: other_item.id
    )

    assert_raises(ArgumentError) do
      service.queue_extraction
    end
  end

  test "queue_extraction accepts valid inventory_item_id" do
    item = create(:inventory_item, user: @user)

    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: @analysis_results,
      inventory_item_id: item.id
    )

    assert_enqueued_with(job: ExtractStockPhotoJob) do
      service.queue_extraction
    end
  end

  test "sanitize_analysis_results handles ActionController::Parameters" do
    params = ActionController::Parameters.new(@analysis_results)
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: params
    )

    assert service.instance_variable_get(:@analysis_results).is_a?(Hash)
  end

  test "sanitize_analysis_results handles Hash with symbol keys" do
    hash_with_symbols = {
      name: "Test",
      category_name: "Tops",
      colors: [ "blue" ]
    }
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: hash_with_symbols
    )

    result = service.instance_variable_get(:@analysis_results)
    assert result.is_a?(Hash)
    assert_equal "Test", result["name"]
  end

  test "sanitize_analysis_results handles JSON string" do
    json_string = @analysis_results.to_json
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: json_string
    )

    result = service.instance_variable_get(:@analysis_results)
    assert result.is_a?(Hash)
    assert_equal "Blue Shirt", result["name"]
  end

  test "sanitize_analysis_results filters out non-permitted keys" do
    hash_with_extra = @analysis_results.merge(
      "malicious_key" => "value",
      "another_bad_key" => "data"
    )
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: hash_with_extra
    )

    result = service.instance_variable_get(:@analysis_results)
    assert_not result.key?("malicious_key")
    assert_not result.key?("another_bad_key")
  end

  test "sanitize_analysis_results returns empty hash for non-hash non-string" do
    service = StockPhotoExtractionService.new(
      image_blob: @image_blob,
      user: @user,
      analysis_results: [ "array", "not", "hash" ]
    )

    result = service.instance_variable_get(:@analysis_results)
    assert result.is_a?(Hash)
  end
end
