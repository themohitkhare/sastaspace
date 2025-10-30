require "test_helper"

class InventoryItemsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)

    # Stub authentication and current_user for HTML controller
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "index renders successfully with filters and pagination" do
    create_list(:inventory_item, 3, :clothing, user: @user, category: @category)

    get inventory_items_path, params: { search: "Item", color: "blue", season: "summer", page: 1 }
    assert_response :success
  end

  test "new renders successfully" do
    get new_inventory_item_path
    assert_response :success
  end

  test "create creates item and redirects on success" do
    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Shirt",
          description: "Nice shirt",
          category_id: @category.id,
          purchase_price: 19.99,
          purchase_date: Date.today,
          color: "blue",
          size: "M"
        }
      }
    end
    assert_redirected_to inventory_items_path
  end

  test "create attaches primary and additional images when provided" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    addl = [ fixture_file_upload("sample_image.jpg", "image/jpeg"), fixture_file_upload("sample_image.jpg", "image/jpeg") ]

    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "With Images",
          description: "desc",
          category_id: @category.id,
          purchase_price: 10,
          purchase_date: Date.today,
          primary_image: file,
          additional_images: addl
        }
      }
    end
    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?
    assert_equal 2, item.additional_images.count
    assert_redirected_to inventory_items_path
  end

  test "create renders errors on failure" do
    post inventory_items_path, params: { inventory_item: { name: nil, category_id: nil } }
    assert_response :unprocessable_entity
  end

  test "edit renders successfully" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    get edit_inventory_item_path(item)
    assert_response :success
  end

  test "update updates item and redirects on success" do
    item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Old")
    patch inventory_item_path(item), params: {
      inventory_item: { name: "New Name", color: "red", size: "L" }
    }
    assert_redirected_to inventory_items_path
    assert_equal "New Name", item.reload.name
  end

  test "update attaches images when provided" do
    item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Photos")
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    addl = [ fixture_file_upload("sample_image.jpg", "image/jpeg") ]

    patch inventory_item_path(item), params: {
      inventory_item: { primary_image: file, additional_images: addl }
    }
    assert_redirected_to inventory_items_path
    assert item.reload.primary_image.attached?
    assert_equal 1, item.additional_images.count
  end

  test "update renders errors on failure" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    patch inventory_item_path(item), params: { inventory_item: { name: nil } }
    assert_response :unprocessable_entity
  end

  test "destroy deletes item and redirects" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    assert_difference -> { @user.inventory_items.count }, -1 do
      delete inventory_item_path(item)
    end
    assert_redirected_to inventory_items_path
  end

  test "bulk_delete deletes selected items and redirects with notice" do
    items = create_list(:inventory_item, 2, :clothing, user: @user, category: @category)
    delete bulk_delete_inventory_items_path, params: { item_ids: items.map(&:id) }
    assert_redirected_to inventory_items_path
  end

  test "bulk_delete with no items shows alert and redirects" do
    delete bulk_delete_inventory_items_path, params: { item_ids: [] }
    assert_redirected_to inventory_items_path
  end
end
