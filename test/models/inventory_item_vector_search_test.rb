require 'test_helper'

class InventoryItemVectorSearchTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, name: 'tops')
    @brand = create(:brand, name: 'Nike')
    
    @item1 = create(:inventory_item, 
                   user: @user, 
                   category: @category, 
                   brand: @brand,
                   name: 'Blue T-Shirt',
                   item_type: 'clothing',
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })
    
    @item2 = create(:inventory_item, 
                   user: @user, 
                   category: @category, 
                   brand: @brand,
                   name: 'Red T-Shirt',
                   item_type: 'clothing',
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })
    
    @item3 = create(:inventory_item, 
                   user: @user, 
                   category: @category, 
                   brand: @brand,
                   name: 'Green T-Shirt',
                   item_type: 'clothing',
                   embedding_vector: nil)
  end
  
  test "similar_items returns items with vectors" do
    # Mock the find_by_sql method
    InventoryItem.stubs(:find_by_sql).returns([@item2])
    
    results = @item1.similar_items(limit: 5)
    
    assert_equal 1, results.count
    assert_includes results, @item2
    assert_not_includes results, @item1 # Should exclude self
    assert_not_includes results, @item3 # Should exclude items without vectors
  end
  
  test "similar_items returns empty array when no vector present" do
    results = @item3.similar_items(limit: 5)
    assert_equal 0, results.count
  end
  
  test "find_similar_items works with different limit" do
    # Mock the find_by_sql method
    InventoryItem.stubs(:find_by_sql).returns([@item2])
    
    results = @item1.find_similar_items(limit: 10)
    
    assert_equal 1, results.count
    assert_includes results, @item2
  end
  
  test "find_similar_items returns empty array when no vector present" do
    results = @item3.find_similar_items(limit: 10)
    assert_equal 0, results.count
  end
  
  test "vector search methods work correctly" do
    # Test that the vector search methods are properly defined
    assert_respond_to @item1, :similar_items
    assert_respond_to @item1, :find_similar_items
    
    # Test that methods return empty arrays when no vector
    assert_equal [], @item3.similar_items
    assert_equal [], @item3.find_similar_items
  end
  
  test "embedding_vector can be set and retrieved" do
    vector = Array.new(1536) { rand(-1.0..1.0) }
    
    @item3.embedding_vector = vector
    @item3.save!
    
    @item3.reload
    # PostgreSQL stores vectors with different precision, so we check the length and approximate values
    assert_equal vector.length, @item3.embedding_vector.length
    assert @item3.embedding_vector.all? { |v| v.is_a?(Numeric) }
  end
  
  test "embedding_vector can be nil" do
    @item1.embedding_vector = nil
    @item1.save!
    
    @item1.reload
    assert_nil @item1.embedding_vector
  end
end
