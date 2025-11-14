require "test_helper"

class VectorSearchServiceTest < ActiveSupport::TestCase
  def setup
    # Clear cache to prevent state leakage between tests
    Rails.cache.clear
    # Reset cache stats to ensure clean state
    Caching::VectorCacheService.reset_stats

    @user = create(:user)
    @category = create(:category, name: "tops")
    @brand = create(:brand)

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

  def teardown
    # Clean up stubs to prevent interference with other tests
    EmbeddingService.unstub_all if EmbeddingService.respond_to?(:unstub_all)
    # Clear cache after each test to prevent state leakage
    Rails.cache.clear
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
    similar_vector = @item1.embedding_vector.map { |v| v + rand(-0.01..0.01) }
    bottom_item = create(:inventory_item,
                         user: @user,
                         category: bottoms_category,
                         name: "Blue Jeans",
                         item_type: "clothing",
                         embedding_vector: similar_vector)

    # Don't stub - let the actual code run
    results = VectorSearchService.recommend_outfit_items(@user, @item1, limit: 5)

    # Should find complementary items (tops -> bottoms)
    assert results.count >= 1, "Should find at least one complementary item"
    assert_includes results, bottom_item
  end

  test "complementary_category? correctly identifies complementary categories" do
    # Tops complement bottoms
    assert VectorSearchService.send(:complementary_category?, "tops", "bottoms")
    assert VectorSearchService.send(:complementary_category?, "tops", "jeans")
    assert VectorSearchService.send(:complementary_category?, "tops", "pants")

    # Dresses complement shoes and accessories (not tops)
    assert VectorSearchService.send(:complementary_category?, "dresses", "shoes")
    assert VectorSearchService.send(:complementary_category?, "dresses", "accessories")

    # Non-complementary pairs
    assert_not VectorSearchService.send(:complementary_category?, "tops", "tops")
    assert_not VectorSearchService.send(:complementary_category?, "tops", "dresses") # Dresses don't need tops
    assert_not VectorSearchService.send(:complementary_category?, "shoes", "tops") # Shoes don't complement tops directly
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

  test "validate_and_sanitize_vector returns nil for non-array" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, "string")
    assert_nil result
  end

  test "validate_and_sanitize_vector returns nil for empty array" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [])
    assert_nil result
  end

  test "validate_and_sanitize_vector returns nil for non-numeric values" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [ 1.0, "invalid", 2.0 ])
    assert_nil result
  end

  test "validate_and_sanitize_vector returns nil for infinite values" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [ 1.0, Float::INFINITY, 2.0 ])
    assert_nil result
  end

  test "validate_and_sanitize_vector returns nil for NaN values" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [ 1.0, Float::NAN, 2.0 ])
    assert_nil result
  end

  test "validate_and_sanitize_vector returns nil for values exceeding bounds" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [ 1.0, 2_000_000.0, 2.0 ])
    assert_nil result
  end

  test "validate_and_sanitize_vector converts string numbers to floats" do
    result = VectorSearchService.send(:validate_and_sanitize_vector, [ "1.0", "2.5", "3.0" ])
    assert_equal [ 1.0, 2.5, 3.0 ], result
  end

  test "validate_and_sanitize_vector returns validated array" do
    input = [ 1.0, 2.5, 3.0, -1.5 ]
    result = VectorSearchService.send(:validate_and_sanitize_vector, input)
    assert_equal input, result
  end

  test "format_vector_string formats correctly" do
    vector = [ 1.0, 2.5, 3.0 ]
    result = VectorSearchService.send(:format_vector_string, vector)
    assert_equal "[1.0,2.5,3.0]", result
  end

  test "complementary_category? returns false for nil categories" do
    assert_not VectorSearchService.send(:complementary_category?, nil, "bottoms")
    assert_not VectorSearchService.send(:complementary_category?, "tops", nil)
    assert_not VectorSearchService.send(:complementary_category?, nil, nil)
  end

  test "complementary_category? handles all complement pairs" do
    complements = {
      "tops" => [ "bottoms", "jeans", "pants", "skirts", "shorts" ],
      "t-shirts" => [ "jeans", "pants", "skirts", "shorts" ],
      "shirts" => [ "jeans", "pants", "skirts" ],
      "bottoms" => [ "tops", "t-shirts", "shirts", "blouses" ],
      "jeans" => [ "tops", "t-shirts", "shirts" ],
      "dresses" => [ "shoes", "boots", "sneakers", "accessories", "bags", "jewelry" ],
      "shoes" => [ "dresses", "bottoms", "jeans", "pants", "skirts" ]
    }

    complements.each do |base, candidates|
      candidates.each do |candidate|
        assert VectorSearchService.send(:complementary_category?, base, candidate),
               "#{base} should complement #{candidate}"
      end
    end
  end

  test "identify_missing_categories identifies missing top" do
    existing = [ "jeans", "shoes" ]
    missing = VectorSearchService.send(:identify_missing_categories, existing)
    assert_includes missing, "top"
  end

  test "identify_missing_categories identifies missing bottom" do
    existing = [ "t-shirts", "shoes" ]
    missing = VectorSearchService.send(:identify_missing_categories, existing)
    assert_includes missing, "bottom"
  end

  test "identify_missing_categories identifies missing shoe" do
    existing = [ "t-shirts", "jeans" ]
    missing = VectorSearchService.send(:identify_missing_categories, existing)
    assert_includes missing, "shoe"
  end

  test "identify_missing_categories returns empty when all present" do
    existing = [ "t-shirts", "jeans", "sneakers" ]
    missing = VectorSearchService.send(:identify_missing_categories, existing)
    assert_empty missing
  end

  test "calculate_style_similarity returns 0.0 when candidate has no vector" do
    item_without_vector = create(:inventory_item, user: @user, embedding_vector: nil)
    result = VectorSearchService.send(:calculate_style_similarity, [ @item1 ], item_without_vector)
    assert_equal 0.0, result
  end

  test "calculate_style_similarity returns 0.0 when no items have vectors" do
    item_without_vector = create(:inventory_item, user: @user, embedding_vector: nil)
    result = VectorSearchService.send(:calculate_style_similarity, [ item_without_vector ], @item1)
    assert_equal 0.0, result
  end

  test "get_suggestion_reason returns complementary reason" do
    bottoms_category = create(:category, name: "bottoms")
    bottom_item = create(:inventory_item, user: @user, category: bottoms_category)
    existing = [ "tops" ]

    result = VectorSearchService.send(:get_suggestion_reason, @item1, bottom_item, existing)
    assert_includes result, "Pairs well"
  end

  test "get_suggestion_reason returns similar style reason" do
    existing = [ "tops" ]
    result = VectorSearchService.send(:get_suggestion_reason, @item1, @item2, existing)
    assert_includes result, "Similar style"
  end

  test "get_suggestion_reason returns generic complement reason" do
    other_category = create(:category, name: "accessories")
    other_item = create(:inventory_item, user: @user, category: other_category)
    existing = [ "tops" ]

    result = VectorSearchService.send(:get_suggestion_reason, @item1, other_item, existing)
    assert_includes result, "Complements"
  end

  test "suggest_outfit_items returns empty for blank outfit_items" do
    result = VectorSearchService.suggest_outfit_items(@user, [], limit: 5)
    assert_equal [], result
  end

  test "suggest_outfit_items returns empty for nil outfit_items" do
    result = VectorSearchService.suggest_outfit_items(@user, nil, limit: 5)
    assert_equal [], result
  end

  test "suggest_outfit_items handles Outfit object" do
    outfit = create(:outfit, user: @user)
    outfit.inventory_items << @item1

    result = VectorSearchService.suggest_outfit_items(@user, outfit, limit: 5)
    assert result.is_a?(Array)
  end

  test "suggest_outfit_items excludes specified item IDs" do
    outfit = create(:outfit, user: @user)
    outfit.inventory_items << @item1

    result = VectorSearchService.suggest_outfit_items(@user, outfit, limit: 5, exclude_ids: [ @item2.id ])
    assert_not_includes result.map(&:id), @item2.id
  end

  test "semantic_search returns empty for blank query" do
    result = VectorSearchService.semantic_search(@user, "", limit: 10)
    assert_equal [], result
  end

  test "semantic_search returns empty for nil query" do
    result = VectorSearchService.semantic_search(@user, nil, limit: 10)
    assert_equal [], result
  end

  test "find_similar_items returns empty for invalid vector" do
    invalid_vector = [ Float::INFINITY, 1.0 ]
    result = VectorSearchService.find_similar_items(@user, invalid_vector, limit: 5)
    assert_equal [], result
  end

  test "find_items_by_image_similarity returns empty for invalid vector" do
    invalid_vector = [ Float::NAN, 1.0 ]
    result = VectorSearchService.find_items_by_image_similarity(@user, invalid_vector, limit: 5)
    assert_equal [], result
  end
end
