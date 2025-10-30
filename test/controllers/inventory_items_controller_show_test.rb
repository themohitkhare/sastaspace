require "test_helper"

class InventoryItemsControllerShowTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "show redirects to edit" do
    get inventory_item_path(@item)
    assert_redirected_to edit_inventory_item_path(@item)
  end
end
