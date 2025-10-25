require "test_helper"

class CategoryTest < ActiveSupport::TestCase
  def setup
    @category = build(:category)
  end

  test "should be valid" do
    assert @category.valid?
  end

  test "name should be present" do
    @category.name = nil
    assert_not @category.valid?
    assert_includes @category.errors[:name], "can't be blank"
  end

  test "name should be unique" do
    @category.save!
    duplicate_category = build(:category, name: @category.name)
    assert_not duplicate_category.valid?
    assert_includes duplicate_category.errors[:name], "has already been taken"
  end

  test "should have predefined clothing categories" do
    assert_equal %w[tops bottoms dresses outerwear undergarments], Category::CLOTHING_CATEGORIES
  end

  test "should have predefined shoes categories" do
    assert_equal %w[sneakers heels boots sandals flats], Category::SHOES_CATEGORIES
  end

  test "should have predefined accessories categories" do
    assert_equal %w[bags belts hats scarves sunglasses], Category::ACCESSORIES_CATEGORIES
  end

  test "should have predefined jewelry categories" do
    assert_equal %w[necklaces rings earrings bracelets watches], Category::JEWELRY_CATEGORIES
  end

  test "for_clothing scope should return clothing categories" do
    clothing_category = create(:category, :clothing)
    shoes_category = create(:category, :shoes)
    
    clothing_categories = Category.for_clothing
    assert_includes clothing_categories, clothing_category
    assert_not_includes clothing_categories, shoes_category
  end

  test "for_shoes scope should return shoes categories" do
    clothing_category = create(:category, :clothing)
    shoes_category = create(:category, :shoes)
    
    shoes_categories = Category.for_shoes
    assert_includes shoes_categories, shoes_category
    assert_not_includes shoes_categories, clothing_category
  end

  test "should restrict destroy when inventory items exist" do
    category = create(:category)
    create(:inventory_item, category: category)
    
    assert_raises(ActiveRecord::DeleteRestrictionError) do
      category.destroy
    end
  end
end
