require "test_helper"

class InventoryItemsControllerNormalizationTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @parent = create(:category, name: "Tops Root")
    @child = Category.create!(name: "T-Shirts", parent_category: @parent, slug: "t-shirts")
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "create normalizes subcategory selection to set parent category and subcategory_id" do
    post inventory_items_path, params: {
      inventory_item: {
        name: "Tee",
        description: "cotton",
        category_id: @child.id,
        purchase_price: 9.99,
        purchase_date: Date.today,
        color: "white",
        size: "M"
      }
    }
    assert_redirected_to inventory_items_path
    item = @user.inventory_items.last
    assert_equal @parent.id, item.category_id
    assert_equal @child.id, item.subcategory_id
  end
end
