require "test_helper"

class InventoryItemsControllerUpdateNormalizationTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    unique_suffix = SecureRandom.hex(4)
    @parent = create(:category, name: "Bottoms Root #{unique_suffix}")
    @child = Category.create!(name: "Jeans #{unique_suffix}", parent_category: @parent, slug: "jeans-#{unique_suffix}")
    @item = create(:inventory_item, :clothing, user: @user, category: @parent)
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "update normalizes when selecting a subcategory" do
    patch inventory_item_path(@item), params: { inventory_item: { category_id: @child.id } }
    assert_redirected_to inventory_items_path
    @item.reload
    assert_equal @parent.id, @item.category_id
    assert_equal @child.id, @item.subcategory_id
  end
end
