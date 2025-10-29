require "test_helper"

class VectorSearchServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, name: "tops")
    @brand = create(:brand, name: "Nike")

    # Create inventory items with mock vectors
    @item1 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Blue T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    @item2 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Red T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    @item3 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Green T-Shirt",
                   item_type: "clothing",
                   embedding_vector: nil) # No vector
  end

  test "find_similar_items returns items with vectors" do
    query_vector = Array.new(1536) { rand(-1.0..1.0) }

    # Don't stub - let the actual code run
    # This will exercise the actual VectorSearchService code
    results = VectorSearchService.find_similar_items(@user, query_vector, limit: 5)

    # Should find both items that have vectors
    assert_equal 2, results.count
    assert_includes results, @item1
    assert_includes results, @item2
    assert_not_includes results, @item3
  end

  test "semantic_search generates embedding and finds similar items" do
    query_text = "blue casual shirt"

    # Mock the embedding service (external dependency)
    mock_embedding = Array.new(1536) { rand(-1.0..1.0) }
    EmbeddingService.stubs(:generate_text_embedding).returns(mock_embedding)

    # Let the actual service code run
    results = VectorSearchService.semantic_search(@user, query_text, limit: 10)

    # Should return at least 1 item (may return both items if they match)
    assert results.count >= 1, "Should return at least one result"
  end

  test "semantic_search returns empty array when embedding generation fails" do
    query_text = "blue casual shirt"

    # Mock embedding generation failure (external dependency)
    EmbeddingService.stubs(:generate_text_embedding).returns(nil)

    results = VectorSearchService.semantic_search(@user, query_text, limit: 10)

    assert_equal 0, results.count
  end

  test "find_items_by_image_similarity works with image vectors" do
    image_vector = Array.new(1536) { rand(-1.0..1.0) }

    # Don't stub - let the actual code run
    results = VectorSearchService.find_items_by_image_similarity(@user, image_vector, limit: 5)

    # Should find both items that have vectors
    assert_equal 2, results.count
    assert_includes results, @item1
    assert_includes results, @item2
  end

  test "recommend_outfit_items finds complementary items" do
    bottoms_category = create(:category, name: "bottoms")
    bottom_item = create(:inventory_item,
                         user: @user,
                         category: bottoms_category,
                         name: "Blue Jeans",
                         item_type: "clothing",
                         embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    # Don't stub - let the actual code run
    results = VectorSearchService.recommend_outfit_items(@user, @item1, limit: 3)

    # Should find complementary items (tops -> bottoms)
    assert results.count >= 1, "Should find at least one complementary item"
    assert_includes results, bottom_item
  end

  test "complementary_category? correctly identifies complementary categories" do
    assert VectorSearchService.send(:complementary_category?, "tops", "bottoms")
    assert VectorSearchService.send(:complementary_category?, "tops", "dresses")
    assert VectorSearchService.send(:complementary_category?, "dresses", "shoes")
    assert_not VectorSearchService.send(:complementary_category?, "tops", "tops")
    assert_not VectorSearchService.send(:complementary_category?, "shoes", "tops")
  end

  test "find_similar_items returns empty array for nil vector" do
    results = VectorSearchService.find_similar_items(@user, nil, limit: 5)
    assert_equal 0, results.count
  end

  test "find_items_by_image_similarity returns empty array for nil vector" do
    results = VectorSearchService.find_items_by_image_similarity(@user, nil, limit: 5)
    assert_equal 0, results.count
  end

  test "recommend_outfit_items returns empty array when base item has no vector" do
    results = VectorSearchService.recommend_outfit_items(@user, @item3, limit: 3)
    assert_equal 0, results.count
  end
end
