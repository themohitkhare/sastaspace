require "test_helper"

class TagTest < ActiveSupport::TestCase
  setup do
    @tag = build(:tag)
  end

  test "should be valid" do
    assert @tag.valid?
  end

  test "name should be present" do
    @tag.name = nil
    assert_not @tag.valid?
    assert_includes @tag.errors[:name], "can't be blank"
  end

  test "name should be unique" do
    @tag.save!
    duplicate_tag = build(:tag, name: @tag.name)
    assert_not duplicate_tag.valid?
    assert_includes duplicate_tag.errors[:name], "has already been taken"
  end

  test "can create tag" do
    tag = Tag.create!(name: "Casual #{SecureRandom.hex(4)}")
    assert tag.persisted?
  end

  test "can have many inventory_items through inventory_tags" do
    user = create(:user)
    category = create(:category, :clothing)
    tag = create(:tag)
    item1 = create(:inventory_item, user: user, category: category)
    item2 = create(:inventory_item, user: user, category: category)
    
    InventoryTag.create!(inventory_item: item1, tag: tag)
    InventoryTag.create!(inventory_item: item2, tag: tag)
    
    assert_equal 2, tag.inventory_items.count
    assert_includes tag.inventory_items, item1
    assert_includes tag.inventory_items, item2
  end

  test "destroying tag destroys associated inventory_tags" do
    user = create(:user)
    category = create(:category, :clothing)
    tag = create(:tag)
    item = create(:inventory_item, user: user, category: category)
    inventory_tag = InventoryTag.create!(inventory_item: item, tag: tag)
    
    assert_difference -> { InventoryTag.count }, -1 do
      tag.destroy
    end
    
    # Inventory item should still exist
    assert item.reload.persisted?
  end
end
