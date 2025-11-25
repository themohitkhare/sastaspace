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

  test "build_analysis_results_from_item builds correct hash" do
    category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    brand = create(:brand, name: "Nike #{SecureRandom.hex(4)}")
    item = create(:inventory_item,
      user: @user,
      category: category,
      brand: brand,
      name: "Blue Shirt",
      description: "A nice blue shirt",
      color: "blue",
      material: "cotton",
      style_notes: "casual"
    )

    results = StockPhotoExtractionService.build_analysis_results_from_item(item)

    assert_equal "Blue Shirt", results["name"]
    assert_equal "A nice blue shirt", results["description"]
    assert_equal category.name, results["category_name"]
    assert_equal category.name, results["category_matched"]
    assert_equal "cotton", results["material"]
    assert_equal "casual", results["style_notes"]
    assert_equal brand.name, results["brand_matched"]
    assert_equal [ "blue" ], results["colors"]
    assert_equal true, results["gender_appropriate"]
    assert_equal 0.9, results["confidence"]
  end

  test "queue_for_item queues extraction for item with primary image" do
    category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category)
    item.primary_image.attach(@image_blob)

    assert_enqueued_with(job: ExtractStockPhotoJob) do
      job_id = StockPhotoExtractionService.queue_for_item(item)
      assert_not_nil job_id
    end
  end

  test "queue_for_item returns nil for item without primary image" do
    item = create(:inventory_item, user: @user)

    job_id = StockPhotoExtractionService.queue_for_item(item)
    assert_nil job_id
  end

  test "queue_for_item clears completion timestamp when clear_completion_timestamp is true" do
    category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category)
    item.primary_image.attach(@image_blob)
    item.update_column(:stock_photo_extraction_completed_at, Time.current)

    assert_enqueued_with(job: ExtractStockPhotoJob) do
      StockPhotoExtractionService.queue_for_item(item, clear_completion_timestamp: true)
    end

    assert_nil item.reload.stock_photo_extraction_completed_at
  end

  test "queue_for_item does not clear completion timestamp by default" do
    category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category)
    item.primary_image.attach(@image_blob)
    timestamp = Time.current
    item.update_column(:stock_photo_extraction_completed_at, timestamp)

    assert_enqueued_with(job: ExtractStockPhotoJob) do
      StockPhotoExtractionService.queue_for_item(item)
    end

    assert_equal timestamp.to_i, item.reload.stock_photo_extraction_completed_at.to_i
  end
end
