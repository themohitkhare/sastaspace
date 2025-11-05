require "test_helper"

class InventoryItemItemTypeDeriveTest < ActiveSupport::TestCase
  test "item_type derives from top-level Shoes category" do
    user = create(:user)
    shoes = Category.find_or_create_by!(name: "Shoes") do |c|
      c.parent_category = nil
    end
    sneakers = Category.find_or_create_by!(name: "Sneakers") do |c|
      c.parent_category = shoes
    end
    item = create(:inventory_item, user: user, category: sneakers, subcategory: sneakers, metadata: { size: "9" })
    assert_equal "shoes", item.item_type
  end

  test "item_type maps from category name when no parent" do
    user = create(:user)
    unique_name = "Earrings #{SecureRandom.hex(4)}"
    earrings = create(:category, name: unique_name, parent_category: nil)
    item = create(:inventory_item, user: user, category: earrings)
    assert_equal "jewelry", item.item_type
  end

  test "additional_image_variants returns empty hash for nil image" do
    item = build(:inventory_item)
    assert_equal({}, item.additional_image_variants(nil))
  end
end
