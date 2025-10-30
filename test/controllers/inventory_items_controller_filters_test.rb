require "test_helper"

class InventoryItemsControllerFiltersTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Blue Tee", metadata: { color: "blue", season: "summer" })
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "index applies category, color, season and search filters" do
    get inventory_items_path, params: { category_id: @category.id, color: "blue", season: "summer", search: "Blue" }
    assert_response :success
  end
end
