require "test_helper"

class OutfitItemTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @outfit = create(:outfit, user: @user)
    @inventory_item = create(:inventory_item, user: @user, category: @category)
  end

  test "should be valid with outfit and inventory_item" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, position: 0)
    assert outfit_item.valid?
    assert outfit_item.save
  end

  test "should require outfit" do
    outfit_item = OutfitItem.new(inventory_item: @inventory_item, position: 0)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:outfit], "must exist"
  end

  test "should require inventory_item" do
    outfit_item = OutfitItem.new(outfit: @outfit, position: 0)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:inventory_item], "must exist"
  end

  test "position should accept nil" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, position: nil)
    assert outfit_item.valid?
  end

  test "position should accept zero or positive numbers" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, position: 0)
    assert outfit_item.valid?

    outfit_item.position = 5
    assert outfit_item.valid?
  end

  test "position should reject negative numbers" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, position: -1)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:position], "must be greater than or equal to 0"
  end

  test "can create multiple outfit_items for same outfit" do
    item2 = create(:inventory_item, user: @user, category: @category)

    outfit_item1 = OutfitItem.create!(outfit: @outfit, inventory_item: @inventory_item, position: 0)
    outfit_item2 = OutfitItem.create!(outfit: @outfit, inventory_item: item2, position: 1)

    assert_equal 2, @outfit.outfit_items.count
    assert_equal [ @inventory_item, item2 ], @outfit.inventory_items.to_a
  end

  test "can create multiple outfit_items with same inventory_item in different outfits" do
    outfit2 = create(:outfit, user: @user)

    outfit_item1 = OutfitItem.create!(outfit: @outfit, inventory_item: @inventory_item, position: 0)
    outfit_item2 = OutfitItem.create!(outfit: outfit2, inventory_item: @inventory_item, position: 0)

    assert_equal 1, @outfit.outfit_items.count
    assert_equal 1, outfit2.outfit_items.count
  end

  test "destroying outfit destroys associated outfit_items" do
    OutfitItem.create!(outfit: @outfit, inventory_item: @inventory_item, position: 0)

    assert_difference -> { OutfitItem.count }, -1 do
      @outfit.destroy
    end
  end

  test "destroying inventory_item while referenced by outfit_item raises FK violation" do
    OutfitItem.create!(outfit: @outfit, inventory_item: @inventory_item, position: 0)

    assert_raises(ActiveRecord::InvalidForeignKey) do
      @inventory_item.destroy
    end
  end

  test "worn_count defaults to 0" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item)
    assert_equal 0, outfit_item.worn_count
  end

  test "worn_count can be set explicitly" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, worn_count: 5)
    assert_equal 5, outfit_item.worn_count
  end

  test "worn_count accepts nil" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, worn_count: nil)
    assert outfit_item.valid?
  end

  test "worn_count should accept zero or positive numbers" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, worn_count: 0)
    assert outfit_item.valid?

    outfit_item.worn_count = 5
    assert outfit_item.valid?
  end

  test "worn_count should reject negative numbers" do
    outfit_item = OutfitItem.new(outfit: @outfit, inventory_item: @inventory_item, worn_count: -1)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:worn_count], "must be greater than or equal to 0"
  end

  test "worn_recently scope returns items worn in last 30 days" do
    recent_item = OutfitItem.create!(
      outfit: @outfit,
      inventory_item: @inventory_item,
      last_worn_at: 10.days.ago
    )

    old_item = OutfitItem.create!(
      outfit: @outfit,
      inventory_item: create(:inventory_item, user: @user, category: @category),
      last_worn_at: 31.days.ago
    )

    recent = OutfitItem.worn_recently.to_a
    assert_includes recent, recent_item
    assert_not_includes recent, old_item
  end
end
