require "test_helper"

class VectorSearchServiceEdgeTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
  end

  test "complementary_category? returns true for complementary pairs" do
    assert VectorSearchService.send(:complementary_category?, "tops", "bottoms")
    assert VectorSearchService.send(:complementary_category?, "bottoms", "tops")
    assert VectorSearchService.send(:complementary_category?, "dresses", "shoes")
    assert VectorSearchService.send(:complementary_category?, "accessories", "tops")
  end

  test "complementary_category? returns false for non-complementary pairs" do
    assert_equal false, VectorSearchService.send(:complementary_category?, "tops", "tops")
    assert_equal false, VectorSearchService.send(:complementary_category?, "tops", "shoes")
  end

  test "complementary_category? is case insensitive" do
    assert VectorSearchService.send(:complementary_category?, "TOPS", "bottoms")
    assert VectorSearchService.send(:complementary_category?, "tops", "BOTTOMS")
  end

  test "recommend_outfit_items limits results to specified limit" do
    base_item = create(:inventory_item, :clothing, user: @user)
    base_item.update!(embedding_vector: [ 0.1 ] * 1536)

    # Create many similar items
    10.times do |i|
      item = create(:inventory_item, :clothing, user: @user, category: base_item.category, brand: base_item.brand, name: "Similar #{i}")
      item.update!(embedding_vector: [ 0.1 ] * 1536)
    end

    results = VectorSearchService.recommend_outfit_items(@user, base_item, limit: 3)
    assert results.length <= 3
  end
end
