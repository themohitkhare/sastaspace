require "test_helper"

class ExtractStockPhotoJobPrimaryImageTest < ActiveJob::TestCase
  def setup
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
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
    @job_id = SecureRandom.uuid
  end

  def teardown
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "job replaces primary image with extracted image" do
    # Create inventory item with the original image blob as primary image
    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(@image_blob)
    inventory_item.reload

    # Verify initial state
    assert inventory_item.primary_image.attached?
    assert_equal @image_blob.id, inventory_item.primary_image.blob.id
    assert_equal 0, inventory_item.additional_images.count

    # Create valid PNG image data for extracted image
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Perform the job
    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    # Reload to get latest state
    inventory_item.reload

    # Verify the job completed
    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "completed", status["status"], "Job should complete successfully"

    # CRITICAL ASSERTIONS: Verify primary image was replaced
    assert inventory_item.primary_image.attached?, "Primary image should still be attached"

    extracted_blob_id = status["data"]["extracted_blob_id"]
    assert extracted_blob_id.present?, "Extracted blob ID should be in status"

    # The primary image should now be the extracted blob, NOT the original
    assert_not_equal @image_blob.id, inventory_item.primary_image.blob.id,
      "Primary image should NOT be the original blob anymore"
    assert_equal extracted_blob_id, inventory_item.primary_image.blob.id,
      "Primary image should be the extracted blob"

    # Verify original image was moved to additional_images
    assert_equal 1, inventory_item.additional_images.count,
      "Original image should be moved to additional_images"
    assert inventory_item.additional_images.any? { |img| img.blob.id == @image_blob.id },
      "Original blob should be in additional_images"

    # Verify the status data reflects this
    assert_equal true, status["data"]["primary_image_replaced"],
      "Status should indicate primary image was replaced"
    assert_equal true, status["data"]["original_moved_to_additional"],
      "Status should indicate original was moved to additional"
  end

  test "job handles case where inventory item not found" do
    # Don't create an inventory item - blob is orphaned

    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Should complete but not attach to any item
    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "completed", status["status"]
    assert_nil status["data"]["inventory_item_id"], "Should not have inventory_item_id"
    assert_not status["data"]["primary_image_replaced"],
      "Should indicate primary image was NOT replaced (got: #{status["data"]["primary_image_replaced"].inspect})"
  end

  test "job handles case where primary image changed before job runs" do
    # Scenario: User uploads image A (job queued), then updates to image B before job runs.
    # Job should probably NOT replace image B with extracted image A.

    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(@image_blob) # Image A
    inventory_item.reload

    # Simulate user changing primary image to Image B
    # Detach first to prevent purging of @image_blob (we want it to exist for the job)
    inventory_item.primary_image.detach

    image_b_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image_b.jpg",
      content_type: "image/jpeg"
    )
    inventory_item.primary_image.attach(image_b_blob)
    inventory_item.reload

    # Verify Image B is primary
    assert_equal image_b_blob.id, inventory_item.primary_image.blob.id

    # Create valid PNG image data for extracted image A
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Perform the job for Image A
    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    inventory_item.reload
    status = ExtractStockPhotoJob.get_status(@job_id)

    # Assertions: What SHOULD happen?
    assert_equal "completed", status["status"], "Job failed with error: #{status["error"]}"
    assert status["data"].present?, "Status data should be present"

    # Ideally, it should NOT replace Image B with Extracted A.
    # But currently logic falls back to finding item by blob A.
    # Blob A is detached (replaced by B).
    # So it searches for item with blob A.
    # It won't find it attached to inventory_item (primary is B).
    # It might find it if it was moved to additional? But we didn't move it to additional in this test setup (attach replaces).

    # So inventory_item should NOT be found/verified.
    # And primary image should stay Image B.

    assert_equal image_b_blob.id, inventory_item.primary_image.blob.id, "Primary image should remain Image B"

    # Status should indicate it didn't replace primary
    assert_not status["data"]["primary_image_replaced"], "Should NOT replace primary image if it changed"
  end

  test "job attaches to additional images if primary image changed but item ID is known" do
    # Scenario: User uploads image A, updates to image B. Job runs for A.
    # We still want the extracted result of A attached to the item (maybe in additional images)
    # instead of losing it.

    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(@image_blob) # Image A
    inventory_item.reload

    # Simulate user changing primary image to Image B
    # Detach first to prevent purging of @image_blob (we want it to exist for the job)
    inventory_item.primary_image.detach

    image_b_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image_b.jpg",
      content_type: "image/jpeg"
    )
    inventory_item.primary_image.attach(image_b_blob)
    inventory_item.reload

    # Create valid PNG image data
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Run job
    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    inventory_item.reload
    status = ExtractStockPhotoJob.get_status(@job_id)

    assert_equal "completed", status["status"], "Job failed with error: #{status["error"]}"

    # Currently, this FAILS to attach anything because it discards the item.
    # We want to fix it so it attaches to additional_images.

    # assert inventory_item.additional_images.any?, "Should attach extracted image to additional images if primary changed"
    # BUT FOR NOW, verifying the CURRENT BROKEN BEHAVIOR:

    assert_equal image_b_blob.id, inventory_item.primary_image.blob.id
    assert inventory_item.additional_images.count > 0, "Should attach extracted image to additional images if primary changed"
    assert inventory_item.additional_images.any? { |img| img.blob.id == status["data"]["extracted_blob_id"] }, "Extracted image should be in additional images"
  end
end
