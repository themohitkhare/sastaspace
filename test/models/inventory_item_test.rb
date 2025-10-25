require "test_helper"

class InventoryItemTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, :clothing)
    @brand = create(:brand)
    @inventory_item = build(:inventory_item, :clothing, user: @user, category: @category, brand: @brand)
  end

  test "should be valid" do
    assert @inventory_item.valid?
  end

  test "name should be present" do
    @inventory_item.name = nil
    assert_not @inventory_item.valid?
    assert_includes @inventory_item.errors[:name], "can't be blank"
  end

  test "item_type should be present" do
    @inventory_item.item_type = nil
    assert_not @inventory_item.valid?
    assert_includes @inventory_item.errors[:item_type], "can't be blank"
  end

  test "category should be present" do
    @inventory_item.category = nil
    assert_not @inventory_item.valid?
    assert_includes @inventory_item.errors[:category], "can't be blank"
  end

  test "should belong to user" do
    assert_equal @user, @inventory_item.user
  end

  test "should belong to category" do
    assert_equal @category, @inventory_item.category
  end

  test "should belong to brand" do
    assert_equal @brand, @inventory_item.brand
  end

  test "should have default status of active" do
    item = create(:inventory_item, :clothing)
    assert_equal 'active', item.status
  end

  test "should have default wear_count of 0" do
    item = create(:inventory_item, :clothing)
    assert_equal 0, item.wear_count
  end

  test "should increment wear count" do
    item = create(:inventory_item, :clothing)
    initial_count = item.wear_count
    
    item.increment_wear_count!
    
    assert_equal initial_count + 1, item.wear_count
    assert_not_nil item.last_worn_at
  end

  test "should validate clothing size" do
    item = build(:inventory_item, :clothing, metadata: { size: 'XL' })
    assert item.valid?
    
    item.metadata = { size: 'INVALID_SIZE' }
    assert_not item.valid?
    assert_includes item.errors[:size], 'is not a valid clothing size'
  end

  test "should validate shoe size" do
    item = build(:inventory_item, :shoes, metadata: { size: '9' })
    assert item.valid?
    
    item.metadata = { size: '20' } # Invalid shoe size
    assert_not item.valid?
    assert_includes item.errors[:size], 'is not a valid shoe size'
  end

  test "metadata_summary should return compact metadata" do
    item = create(:inventory_item, metadata: { 
      color: 'blue', 
      size: 'M', 
      material: 'cotton',
      season: 'summer',
      occasion: 'casual'
    })
    
    summary = item.metadata_summary
    assert_equal 'blue', summary[:color]
    assert_equal 'M', summary[:size]
    assert_equal 'cotton', summary[:material]
    assert_equal 'summer', summary[:season]
    assert_equal 'casual', summary[:occasion]
  end

  test "by_type scope should filter by item type" do
    clothing_item = create(:inventory_item, :clothing)
    shoes_item = create(:inventory_item, :shoes)
    
    clothing_items = InventoryItem.by_type('clothing')
    assert_includes clothing_items, clothing_item
    assert_not_includes clothing_items, shoes_item
  end

  test "by_category scope should filter by category name" do
    tops_category = create(:category, name: 'tops')
    bottoms_category = create(:category, name: 'bottoms')
    
    tops_item = create(:inventory_item, :clothing, name: "Tops Item", category: tops_category)
    bottoms_item = create(:inventory_item, :clothing, name: "Bottoms Item", category: bottoms_category)
    
    tops_items = InventoryItem.by_category('tops')
    assert_includes tops_items, tops_item
    assert_not_includes tops_items, bottoms_item
  end

  test "by_season scope should filter by season metadata" do
    summer_item = create(:inventory_item, :clothing, name: "Summer Item", metadata: { season: 'summer' })
    winter_item = create(:inventory_item, :clothing, name: "Winter Item", metadata: { season: 'winter' })
    
    summer_items = InventoryItem.by_season('summer')
    assert_includes summer_items, summer_item
    assert_not_includes summer_items, winter_item
  end

  test "by_color scope should filter by color metadata" do
    blue_item = create(:inventory_item, :clothing, name: "Blue Item", metadata: { color: 'blue' })
    red_item = create(:inventory_item, :clothing, name: "Red Item", metadata: { color: 'red' })
    
    blue_items = InventoryItem.by_color('blue')
    assert_includes blue_items, blue_item
    assert_not_includes blue_items, red_item
  end

  test "recently_worn scope should return items worn recently" do
    recently_worn = create(:inventory_item, :clothing, last_worn_at: 1.day.ago)
    never_worn = create(:inventory_item, :clothing, last_worn_at: nil)
    
    recently_worn_items = InventoryItem.recently_worn
    assert_includes recently_worn_items, recently_worn
    assert_not_includes recently_worn_items, never_worn
  end

  test "never_worn scope should return items never worn" do
    recently_worn = create(:inventory_item, :clothing, last_worn_at: 1.day.ago)
    never_worn = create(:inventory_item, :clothing, last_worn_at: nil)
    
    never_worn_items = InventoryItem.never_worn
    assert_includes never_worn_items, never_worn
    assert_not_includes never_worn_items, recently_worn
  end

  test "most_worn scope should return items ordered by wear count" do
    low_wear = create(:inventory_item, :clothing, name: "Low Wear Item", wear_count: 1)
    high_wear = create(:inventory_item, :clothing, name: "High Wear Item", wear_count: 10)
    
    most_worn_items = InventoryItem.most_worn
    assert_equal high_wear, most_worn_items.first
    assert_equal low_wear, most_worn_items.last
  end

  test "should have many tags through inventory_tags" do
    item = create(:inventory_item, :clothing)
    tag1 = create(:tag)
    tag2 = create(:tag)
    
    item.tags << tag1
    item.tags << tag2
    
    assert_includes item.tags, tag1
    assert_includes item.tags, tag2
    assert_equal 2, item.tags.count
  end

  test "similar_items should return items of same type" do
    clothing_item1 = create(:inventory_item, :clothing, name: "Clothing Item 1")
    clothing_item2 = create(:inventory_item, :clothing, name: "Clothing Item 2")
    shoes_item = create(:inventory_item, :shoes, name: "Shoes Item")
    
    similar = clothing_item1.similar_items
    assert_includes similar, clothing_item2
    assert_not_includes similar, shoes_item
    assert_not_includes similar, clothing_item1 # Should not include self
  end
end
