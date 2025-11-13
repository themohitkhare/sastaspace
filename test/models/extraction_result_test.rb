require "test_helper"

class ExtractionResultTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @analysis = create(:clothing_analysis, user: @user, image_blob_id: @image_blob.id)
  end

  test "can create extraction_result" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Blue Shirt",
        "category" => "tops"
      },
      status: "pending"
    )

    assert_not_nil result.id
    assert_equal @analysis, result.clothing_analysis
    assert_equal "pending", result.status
  end

  test "belongs to clothing_analysis" do
    result = create(:extraction_result, clothing_analysis: @analysis)
    assert_equal @analysis, result.clothing_analysis
  end

  test "status has default value" do
    # Status has a default value of "pending", so it's always present
    result = ExtractionResult.new(clothing_analysis: @analysis, item_data: {})
    assert_equal "pending", result.status
    assert result.valid?
  end

  test "validates extraction_quality range" do
    result = ExtractionResult.new(
      clothing_analysis: @analysis,
      status: "completed",
      extraction_quality: 1.5
    )
    assert_not result.valid?
    assert_includes result.errors[:extraction_quality], "must be in 0.0..1.0"
  end

  test "allows nil extraction_quality" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "pending",
      extraction_quality: nil
    )
    assert result.valid?
    assert_nil result.extraction_quality
  end

  test "status enum works correctly" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "pending"
    )

    assert result.pending?
    assert_not result.completed?
    assert_not result.failed?

    result.update!(status: "completed")
    assert result.completed?
    assert_not result.pending?

    result.update!(status: "failed")
    assert result.failed?
    assert_not result.completed?
  end

  test "default status is pending" do
    result = ExtractionResult.new(clothing_analysis: @analysis)
    assert_equal "pending", result.status
  end

  test "successful scope returns completed results" do
    completed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )
    failed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "failed"
    )

    successful_results = ExtractionResult.successful
    assert_includes successful_results, completed
    assert_not_includes successful_results, failed
  end

  test "failed scope returns failed results" do
    completed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "completed"
    )
    failed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "failed"
    )

    failed_results = ExtractionResult.failed
    assert_includes failed_results, failed
    assert_not_includes failed_results, completed
  end

  test "pending_or_processing scope returns pending and processing results" do
    pending = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "pending"
    )
    processing = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "processing"
    )
    completed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "completed"
    )

    pending_or_processing = ExtractionResult.pending_or_processing
    assert_includes pending_or_processing, pending
    assert_includes pending_or_processing, processing
    assert_not_includes pending_or_processing, completed
  end

  test "item_data_hash returns hash when item_data is hash" do
    item_data = { "id" => "item_001", "item_name" => "Shirt" }
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: item_data,
      status: "pending"
    )

    assert_equal item_data, result.item_data_hash
    assert result.item_data_hash.is_a?(Hash)
  end

  test "item_data_hash returns empty hash when item_data is not hash" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: "invalid",
      status: "pending"
    )

    assert_equal({}, result.item_data_hash)
    assert result.item_data_hash.is_a?(Hash)
  end

  test "item_name returns item_name from item_data" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "item_name" => "Blue Shirt" },
      status: "pending"
    )

    assert_equal "Blue Shirt", result.item_name
  end

  test "item_name returns Unknown Item when item_name not present" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001" },
      status: "pending"
    )

    assert_equal "Unknown Item", result.item_name
  end

  test "item_name handles symbol keys" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { item_name: "Red Dress" },
      status: "pending"
    )

    assert_equal "Red Dress", result.item_name
  end

  test "item_id returns id from item_data" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001" },
      status: "pending"
    )

    assert_equal "item_001", result.item_id
  end

  test "item_id handles symbol keys" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { id: "item_002" },
      status: "pending"
    )

    assert_equal "item_002", result.item_id
  end

  test "extracted_image_blob returns blob when extracted_image_blob_id present" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      extracted_image_blob_id: @image_blob.id,
      status: "completed"
    )

    assert_equal @image_blob, result.extracted_image_blob
  end

  test "extracted_image_blob returns nil when extracted_image_blob_id not present" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "pending"
    )

    assert_nil result.extracted_image_blob
  end

  test "extracted_image_blob returns nil when blob not found" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      extracted_image_blob_id: 99999,
      status: "completed"
    )

    assert_nil result.extracted_image_blob
  end

  test "extraction_successful? returns true for completed with blob" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    assert result.extraction_successful?
  end

  test "extraction_successful? returns false for completed without blob" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "completed",
      extracted_image_blob_id: nil
    )

    assert_not result.extraction_successful?
  end

  test "extraction_successful? returns false for pending status" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "pending",
      extracted_image_blob_id: @image_blob.id
    )

    assert_not result.extraction_successful?
  end

  test "extraction_successful? returns false for failed status" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      status: "failed",
      extracted_image_blob_id: @image_blob.id
    )

    assert_not result.extraction_successful?
  end
end
