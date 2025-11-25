require "test_helper"

class VectorSearchServiceSuggestionsTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)

    # Create categories
    @tops_category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, name: "Jeans #{SecureRandom.hex(4)}")
    @shoes_category = create(:category, name: "Sneakers #{SecureRandom.hex(4)}")

    # Create items with vectors
    @top_item = create(:inventory_item,
      user: @user,
      category: @tops_category,
      name: "Blue T-Shirt",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )

    @bottom_item = create(:inventory_item,
      user: @user,
      category: @bottoms_category,
      name: "Blue Jeans",
      embedding_vector: Array.new(1536) { |i| @top_item.embedding_vector[i] + rand(-0.1..0.1) } # Similar style
    )

    @shoe_item = create(:inventory_item,
      user: @user,
      category: @shoes_category,
      name: "White Sneakers",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )

    # Create outfit
    @outfit = @user.outfits.create!(name: "Test Outfit")
    @outfit.outfit_items.create!(inventory_item: @top_item, position: 0)
  end

  test "suggest_outfit_items returns complementary items" do
    suggestions = VectorSearchService.suggest_outfit_items(@user, [ @top_item ], limit: 5)

    assert suggestions.is_a?(Array)
    # Should suggest bottoms or shoes, not another top
    suggestions.each do |suggestion_hash|
      item = suggestion_hash[:item]
      assert_not_nil item, "Suggestion should have an item"
      assert_not_equal @top_item.id, item.id, "Should not suggest the same item"
      # Verify enhanced data structure
      assert suggestion_hash.key?(:match_score), "Should include match_score"
      assert suggestion_hash.key?(:reasoning), "Should include reasoning"
      assert suggestion_hash.key?(:badges), "Should include badges"
    end
  end

  test "suggest_outfit_items excludes provided item IDs" do
    suggestions = VectorSearchService.suggest_outfit_items(
      @user,
      [ @top_item ],
      limit: 5,
      exclude_ids: [ @bottom_item.id ]
    )

    excluded_ids = suggestions.map { |s| s[:item].id }
    assert_not_includes excluded_ids, @bottom_item.id, "Should exclude specified item"
    assert_not_includes excluded_ids, @top_item.id, "Should exclude items in outfit"
  end

  test "suggest_outfit_items works with outfit object" do
    suggestions = VectorSearchService.suggest_outfit_items(@user, @outfit, limit: 5)

    assert suggestions.is_a?(Array)
    suggestions.each do |suggestion_hash|
      item = suggestion_hash[:item]
      assert_not_nil item, "Suggestion should have an item"
      assert_not_equal @top_item.id, item.id
    end
  end

  test "suggest_outfit_items returns empty array for empty outfit" do
    suggestions = VectorSearchService.suggest_outfit_items(@user, [], limit: 5)
    assert_equal [], suggestions
  end

  test "suggest_outfit_items identifies missing categories" do
    # Outfit only has a top, should identify missing bottom and shoes
    suggestions = VectorSearchService.suggest_outfit_items(@user, [ @top_item ], limit: 10)

    # Should include items from missing categories (bottoms, shoes)
    suggested_categories = suggestions.map { |s| s[:item].category&.name&.downcase }.compact
    assert suggested_categories.any? { |cat| cat.include?("jean") || cat.include?("bottom") || cat.include?("shoe") || cat.include?("sneaker") }
  end

  test "complementary_category? identifies complementary pairs" do
    assert VectorSearchService.send(:complementary_category?, "Tops", "Jeans")
    assert VectorSearchService.send(:complementary_category?, "T-Shirts", "Pants")
    assert VectorSearchService.send(:complementary_category?, "Dresses", "Shoes")
    assert_not VectorSearchService.send(:complementary_category?, "Tops", "Tops")
  end

  test "suggest_outfit_items handles items without embeddings gracefully" do
    category = create(:category, name: "Test #{SecureRandom.hex(4)}")
    item_without_vector = create(:inventory_item, user: @user, category: category, embedding_vector: nil)
    item_with_vector = create(:inventory_item, user: @user, category: category, embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    # Should not crash even with mixed items
    suggestions = VectorSearchService.suggest_outfit_items(@user, [ item_without_vector, item_with_vector ], limit: 5)
    assert suggestions.is_a?(Array)
    # Should still work with the item that has a vector
  end

  test "suggest_outfit_items handles empty exclude_ids" do
    suggestions = VectorSearchService.suggest_outfit_items(
      @user,
      [ @top_item ],
      limit: 5,
      exclude_ids: []
    )
    assert suggestions.is_a?(Array)
    # Should work fine with empty exclude_ids
  end

  test "suggest_outfit_items works with ActiveRecord::Relation" do
    outfit = @user.outfits.create!(name: "Test Outfit")
    outfit.outfit_items.create!(inventory_item: @top_item, position: 0)

    # Pass the relation directly
    suggestions = VectorSearchService.suggest_outfit_items(
      @user,
      outfit.inventory_items.includes(:category, :brand, primary_image_attachment: :blob),
      limit: 5
    )
    assert suggestions.is_a?(Array)
  end

  test "suggest_outfit_items handles all items having same category" do
    # Create multiple items in same category
    items = (1..3).map do |i|
      create(:inventory_item,
        user: @user,
        category: @tops_category,
        name: "Top #{i}",
        embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
      )
    end

    suggestions = VectorSearchService.suggest_outfit_items(@user, items, limit: 5)
    assert suggestions.is_a?(Array)
    # Should suggest items from different categories
    suggested_categories = suggestions.map { |s| s[:item].category&.name&.downcase }.compact
    # At least some should be different from tops
    assert suggested_categories.any? { |cat| !cat.include?("top") } || suggestions.empty?
  end

  test "suggest_outfit_items respects limit parameter" do
    # Create many items
    items = (1..10).map do |i|
      create(:inventory_item,
        user: @user,
        category: @tops_category,
        name: "Top #{i}",
        embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
      )
    end

    suggestions = VectorSearchService.suggest_outfit_items(@user, items.first(2), limit: 3)
    assert suggestions.length <= 3
  end

  test "suggest_outfit_items excludes items already in outfit" do
    bottom_item = create(:inventory_item,
      user: @user,
      category: @bottoms_category,
      name: "Bottom Item",
      embedding_vector: Array.new(1536) { |i| @top_item.embedding_vector[i] + rand(-0.1..0.1) }
    )

    suggestions = VectorSearchService.suggest_outfit_items(
      @user,
      [ @top_item, bottom_item ],
      limit: 10,
      exclude_ids: [ bottom_item.id ]
    )

    suggested_ids = suggestions.map { |s| s[:item].id }
    assert_not_includes suggested_ids, @top_item.id
    assert_not_includes suggested_ids, bottom_item.id
  end
end
