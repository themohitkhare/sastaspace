require "test_helper"

class InventoryItemsControllerMetadataTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "update merges color and size into metadata and redirects" do
    patch inventory_item_path(@item), params: {
      inventory_item: { name: "Updated", color: "green", size: "XL" }
    }
    assert_redirected_to inventory_items_path
    @item.reload
    assert_equal "Updated", @item.name
    assert_equal "green", @item.metadata["color"]
    assert_equal "XL", @item.metadata["size"]
  end
end
