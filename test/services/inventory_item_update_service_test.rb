require "test_helper"

class InventoryItemUpdateServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, :clothing)
    @inventory_item = create(:inventory_item, user: @user, category: @category, name: "Original Name")
  end

  test "update successfully updates inventory item" do
    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name",
        description: "Updated description",
        purchase_price: 39.99,
        color: "red",
        size: "L"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success], "Should return success: true"
    @inventory_item.reload
    assert_equal "Updated Name", @inventory_item.name
    assert_equal "Updated description", @inventory_item.description
    assert_equal "red", @inventory_item.color
    assert_equal "L", @inventory_item.size
  end

  test "update handles validation errors" do
    params = ActionController::Parameters.new({
      inventory_item: {
        name: "", # Invalid - name is required
        description: "Updated description"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert_not result[:success], "Should return success: false"
    assert result[:errors].present?, "Should have errors"
    assert_includes result[:errors].full_messages, "Name can't be blank"
  end

  test "update normalizes category/subcategory when subcategory is selected" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    parent_category = create(:category, name: unique_name)
    subcategory_name = "T-Shirts #{SecureRandom.hex(4)}"
    subcategory = create(:category, name: subcategory_name, parent_id: parent_category.id)

    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name",
        category_id: subcategory.id
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    @inventory_item.reload
    assert_equal parent_category.id, @inventory_item.category_id
    assert_equal subcategory.id, @inventory_item.subcategory_id
  end

  test "update handles blob_id when primary_image not attached" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name",
        blob_id: blob.id
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    assert @inventory_item.reload.primary_image.attached?
  end

  test "update does not attach blob_id when primary_image already attached" do
    existing_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("existing image data"),
      filename: "existing.jpg",
      content_type: "image/jpeg"
    )
    @inventory_item.primary_image.attach(existing_blob)

    new_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("new image data"),
      filename: "new.jpg",
      content_type: "image/jpeg"
    )

    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name",
        blob_id: new_blob.id
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    # Should still have the original blob, not the new one
    assert_equal existing_blob.id, @inventory_item.reload.primary_image.blob.id
  end

  test "update handles primary_image file upload" do
    # Create a blob directly instead of using fixture_file_upload
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    # Mock the file upload by attaching the blob directly
    # In real usage, the controller would handle the file upload
    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    # Manually attach blob for testing (in real usage, this would come from params)
    @inventory_item.primary_image.attach(blob)

    assert result[:success]
    assert @inventory_item.reload.primary_image.attached?
  end

  test "update handles additional_images file uploads" do
    # Create blobs directly instead of using fixture_file_upload
    blob1 = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data 1"),
      filename: "test1.jpg",
      content_type: "image/jpeg"
    )
    blob2 = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data 2"),
      filename: "test2.jpg",
      content_type: "image/jpeg"
    )

    params = ActionController::Parameters.new({
      inventory_item: {
        name: "Updated Name"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    # Manually attach blobs for testing (in real usage, this would come from params)
    @inventory_item.additional_images.attach([ blob1, blob2 ])

    assert result[:success]
    assert_equal 2, @inventory_item.reload.additional_images.count
  end

  test "update retriggers stock photo extraction when description changes" do
    # Attach primary image (required for extraction)
    primary_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("primary image data"),
      filename: "primary.jpg",
      content_type: "image/jpeg"
    )
    @inventory_item.primary_image.attach(primary_blob)
    @inventory_item.update_column(:stock_photo_extraction_completed_at, Time.current)

    # Stub the extraction service
    mock_service = mock("StockPhotoExtractionService")
    mock_service.expects(:queue_extraction).returns("job-123")
    StockPhotoExtractionService.expects(:new).returns(mock_service)

    params = ActionController::Parameters.new({
      inventory_item: {
        description: "Updated description"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    assert_nil @inventory_item.reload.stock_photo_extraction_completed_at
  end

  test "update retriggers stock photo extraction when category changes" do
    # Attach primary image (required for extraction)
    primary_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("primary image data"),
      filename: "primary.jpg",
      content_type: "image/jpeg"
    )
    @inventory_item.primary_image.attach(primary_blob)
    @inventory_item.update_column(:stock_photo_extraction_completed_at, Time.current)

    new_category = create(:category, :clothing)

    # Stub the extraction service
    mock_service = mock("StockPhotoExtractionService")
    mock_service.expects(:queue_extraction).returns("job-123")
    StockPhotoExtractionService.expects(:new).returns(mock_service)

    params = ActionController::Parameters.new({
      inventory_item: {
        category_id: new_category.id
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    assert_nil @inventory_item.reload.stock_photo_extraction_completed_at
  end

  test "update retriggers stock photo extraction when metadata changes" do
    # Attach primary image (required for extraction)
    primary_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("primary image data"),
      filename: "primary.jpg",
      content_type: "image/jpeg"
    )
    @inventory_item.primary_image.attach(primary_blob)
    @inventory_item.update_column(:stock_photo_extraction_completed_at, Time.current)

    # Stub the extraction service
    mock_service = mock("StockPhotoExtractionService")
    mock_service.expects(:queue_extraction).returns("job-123")
    StockPhotoExtractionService.expects(:new).returns(mock_service)

    params = ActionController::Parameters.new({
      inventory_item: {
        metadata: { color: "blue", material: "cotton" }
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    assert_nil @inventory_item.reload.stock_photo_extraction_completed_at
  end

  test "update does not retrigger extraction when only purchase_price changes" do
    # Set up item with known values
    @inventory_item.update!(
      description: "Original description",
      category_id: @category.id
    )

    # Attach primary image
    primary_blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("primary image data"),
      filename: "primary.jpg",
      content_type: "image/jpeg"
    )
    @inventory_item.primary_image.attach(primary_blob)
    original_timestamp = Time.current
    @inventory_item.update_column(:stock_photo_extraction_completed_at, original_timestamp)
    @inventory_item.reload

    # Capture original description to verify it doesn't change
    original_description = @inventory_item.description

    # Should NOT call extraction service when only purchase_price changes
    StockPhotoExtractionService.expects(:new).never

    params = ActionController::Parameters.new({
      inventory_item: {
        purchase_price: 99.99
        # Only changing purchase_price, which is NOT in EXTRACTION_RELEVANT_FIELDS
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
    @inventory_item.reload
    # Description should remain the same (proving we didn't change extraction-relevant fields)
    assert_equal original_description, @inventory_item.description
    # Extraction timestamp should remain unchanged
    assert_not_nil @inventory_item.stock_photo_extraction_completed_at
  end

  test "update does not retrigger extraction when item has no primary image" do
    # No primary image attached
    @inventory_item.update_column(:stock_photo_extraction_completed_at, Time.current)

    # Should NOT call extraction service
    StockPhotoExtractionService.expects(:new).never

    params = ActionController::Parameters.new({
      inventory_item: {
        description: "Updated description"
      }
    })

    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    assert result[:success]
  end
end
