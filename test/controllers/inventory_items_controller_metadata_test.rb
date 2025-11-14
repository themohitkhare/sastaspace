require "test_helper"

class InventoryItemsControllerMetadataTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  teardown do
    # Clean up stubs to prevent interference with other tests
    InventoryItemsController.any_instance.unstub_all if InventoryItemsController.any_instance.respond_to?(:unstub_all)
  end

  test "update updates item and redirects" do
    patch inventory_item_path(@item), params: {
      inventory_item: { name: "Updated", description: "New description" }
    }
    assert_redirected_to inventory_items_path
    @item.reload
    assert_equal "Updated", @item.name
    assert_equal "New description", @item.description
  end
end
