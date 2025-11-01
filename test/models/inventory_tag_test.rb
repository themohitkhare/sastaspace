require "test_helper"

class InventoryTagTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    # Use unique category name to avoid collisions
    category_name = "Clothing #{SecureRandom.hex(4)}"
    @category = create(:category, name: category_name)
    @brand = create(:brand)
    @inventory_item = create(:inventory_item, :clothing, user: @user, category: @category, brand: @brand)
    @tag = create(:tag)
  end

  test "inventory_tag belongs to inventory_item" do
    inventory_tag = InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)

    assert_equal @inventory_item, inventory_tag.inventory_item
  end

  test "inventory_tag belongs to tag" do
    inventory_tag = InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)

    assert_equal @tag, inventory_tag.tag
  end

  test "prevents duplicate inventory_item and tag combination" do
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)

    duplicate = InventoryTag.new(inventory_item: @inventory_item, tag: @tag)

    assert_not duplicate.valid?
    assert_includes duplicate.errors[:inventory_item_id], "has already been taken"
  end

  test "allows same tag for different inventory items" do
    item2 = create(:inventory_item, :clothing, user: @user, category: @category, brand: @brand)

    tag1 = InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    tag2 = InventoryTag.create!(inventory_item: item2, tag: @tag)

    assert tag1.persisted?
    assert tag2.persisted?
  end

  test "allows different tags for same inventory item" do
    tag2_name = "Casual #{SecureRandom.hex(4)}"
    tag2 = create(:tag, name: tag2_name)

    tag1 = InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    tag2_record = InventoryTag.create!(inventory_item: @inventory_item, tag: tag2)

    assert tag1.persisted?
    assert tag2_record.persisted?
  end
end
