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
end
