require "test_helper"

class InventoryItemsControllerPaginationTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    create_list(:inventory_item, 3, :clothing, user: @user)
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "index supports page param" do
    get inventory_items_path, params: { page: 2 }
    assert_response :success
  end
end
