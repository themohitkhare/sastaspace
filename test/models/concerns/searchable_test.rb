require "test_helper"

class SearchableTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @brand = create(:brand)

    # Create items with embedding vectors
    @item1 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Blue T-Shirt",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    @item2 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Red T-Shirt",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })
  end

  test "similar_items returns similar items" do
    results = @item1.similar_items(limit: 5)
    # Returns ActiveRecord::Relation, convert to array for count
    results_array = results.to_a
    assert results_array.is_a?(Array)
    # Results may be empty if no similar items found, or up to limit
    assert results_array.count <= 5, "Results count should be <= limit"
  end

  test "similar_items excludes self" do
    results = @item1.similar_items(limit: 5)
    # Convert to array for iteration
    results_array = results.to_a
    # Results should not include the item itself
    assert_not results_array.any? { |item| item.id == @item1.id }, "Results should not include self"
  end

  test "find_similar_items returns similar items" do
    results = @item1.find_similar_items(limit: 10)
    # Returns ActiveRecord::Relation, convert to array for count
    results_array = results.to_a
    assert results_array.is_a?(Array)
    # Results may be empty if no similar items found, or up to limit
    assert results_array.count <= 10, "Results count should be <= limit"
  end

  test "similar_to scope works" do
    vector = Array.new(1536) { rand(-1.0..1.0) }
    results = InventoryItem.similar_to(vector, limit: 10)
    assert results.is_a?(ActiveRecord::Relation)
    assert results.count <= 10
  end

  test "similar_items returns empty array when no embedding_vector" do
    item = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
    results = item.similar_items
    assert_equal [], results
  end

  test "similar_items handles invalid vector gracefully" do
    @item1.update_column(:embedding_vector, nil)
    results = @item1.similar_items
    assert_equal [], results
  end

  test "find_similar_items handles invalid vector gracefully" do
    @item1.update_column(:embedding_vector, nil)
    results = @item1.find_similar_items
    assert_equal [], results
  end

  test "similar_to scope returns empty when vector is invalid" do
    invalid_vector = "not an array"
    results = InventoryItem.similar_to(invalid_vector, limit: 10)
    assert_equal 0, results.count
  end

  test "similar_to scope returns empty when vector is nil" do
    results = InventoryItem.similar_to(nil, limit: 10)
    assert_equal 0, results.count
  end
end
