require "test_helper"

class InventoryTagTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @inventory_item = create(:inventory_item, user: @user, category: @category)
    @tag = create(:tag)
  end

  test "should be valid with inventory_item and tag" do
    inventory_tag = InventoryTag.new(inventory_item: @inventory_item, tag: @tag)
    assert inventory_tag.valid?
    assert inventory_tag.save
  end

  test "should require inventory_item" do
    inventory_tag = InventoryTag.new(tag: @tag)
    assert_not inventory_tag.valid?
    assert_includes inventory_tag.errors[:inventory_item], "must exist"
  end

  test "should require tag" do
    inventory_tag = InventoryTag.new(inventory_item: @inventory_item)
    assert_not inventory_tag.valid?
    assert_includes inventory_tag.errors[:tag], "must exist"
  end

  test "can associate multiple tags with same inventory_item" do
    tag2 = create(:tag)
    
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    InventoryTag.create!(inventory_item: @inventory_item, tag: tag2)
    
    assert_equal 2, @inventory_item.tags.count
    assert_includes @inventory_item.tags, @tag
    assert_includes @inventory_item.tags, tag2
  end

  test "can associate same tag with multiple inventory_items" do
    item2 = create(:inventory_item, user: @user, category: @category)
    
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    InventoryTag.create!(inventory_item: item2, tag: @tag)
    
    assert_equal 2, @tag.inventory_items.count
    assert_includes @tag.inventory_items, @inventory_item
    assert_includes @tag.inventory_items, item2
  end

  test "should prevent duplicate associations" do
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    
    duplicate = InventoryTag.new(inventory_item: @inventory_item, tag: @tag)
    assert_not duplicate.valid?
    # Should have unique constraint error
  end

  test "destroying inventory_item destroys associated inventory_tags" do
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    
    assert_difference -> { InventoryTag.count }, -1 do
      @inventory_item.destroy
    end
    
    # Tag should still exist
    assert @tag.reload.persisted?
  end

  test "destroying tag destroys associated inventory_tags" do
    InventoryTag.create!(inventory_item: @inventory_item, tag: @tag)
    
    assert_difference -> { InventoryTag.count }, -1 do
      @tag.destroy
    end
    
    # Inventory item should still exist
    assert @inventory_item.reload.persisted?
  end
end
