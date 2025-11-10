require "test_helper"

# Test class must not be namespaced to avoid Rails autoloading issues
class VectorCacheServiceTest < ActiveSupport::TestCase
  def setup
    # Use memory store for caching tests (test environment uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
    @category = create(:category, name: "tops")
    @brand = create(:brand)

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

    @query_vector = Array.new(1536) { rand(-1.0..1.0) }

    # Clear cache before each test
    Rails.cache.clear
    ::Caching::VectorCacheService.reset_stats
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "cache_similar_items caches and returns cached results" do
    # First call - cache miss
    call_count = 0
    results1 = ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      call_count += 1
      [ @item1, @item2 ]
    end

    assert_equal 1, call_count, "Block should be called once on cache miss"
    assert_equal 2, results1.count

    # Second call - cache hit
    results2 = ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      call_count += 1
      [ @item1, @item2 ]
    end

    assert_equal 1, call_count, "Block should not be called again on cache hit"
    assert_equal 2, results2.count
    assert_equal results1.map(&:id), results2.map(&:id)
  end

  test "cache_similar_items uses different keys for different vectors" do
    vector1 = Array.new(1536) { 0.1 }
    vector2 = Array.new(1536) { 0.2 }

    call_count = 0
    ::Caching::VectorCacheService.cache_similar_items(@user, vector1, limit: 10) do
      call_count += 1
      [ @item1 ]
    end

    ::Caching::VectorCacheService.cache_similar_items(@user, vector2, limit: 10) do
      call_count += 1
      [ @item2 ]
    end

    assert_equal 2, call_count, "Different vectors should result in different cache entries"
  end

  test "cache_semantic_search caches text-based searches" do
    query_text = "blue shirt"

    call_count = 0
    results1 = ::Caching::VectorCacheService.cache_semantic_search(@user, query_text, limit: 10) do
      call_count += 1
      [ @item1 ]
    end

    assert_equal 1, call_count

    results2 = ::Caching::VectorCacheService.cache_semantic_search(@user, query_text, limit: 10) do
      call_count += 1
      [ @item1 ]
    end

    assert_equal 1, call_count, "Should use cached result"
    assert_equal results1.map(&:id), results2.map(&:id)
  end

  test "cache_outfit_recommendations caches recommendations" do
    call_count = 0
    results1 = ::Caching::VectorCacheService.cache_outfit_recommendations(@user, @item1, limit: 5) do
      call_count += 1
      [ @item2 ]
    end

    assert_equal 1, call_count

    results2 = ::Caching::VectorCacheService.cache_outfit_recommendations(@user, @item1, limit: 5) do
      call_count += 1
      [ @item2 ]
    end

    assert_equal 1, call_count, "Should use cached result"
  end

  test "invalidate_user_cache clears all user caches" do
    # Cache some results
    ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      [ @item1, @item2 ]
    end

    # Verify cache exists
    stats_before = ::Caching::VectorCacheService.cache_stats
    assert stats_before[:hit_count] >= 0

    # Invalidate
    ::Caching::VectorCacheService.invalidate_user_cache(@user)

    # Next call should be a cache miss
    call_count = 0
    ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      call_count += 1
      [ @item1 ]
    end

    assert_equal 1, call_count, "Cache should be invalidated"
  end

  test "invalidate_item_cache clears item-related caches" do
    # Cache some results
    ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      [ @item1, @item2 ]
    end

    # Invalidate item cache
    ::Caching::VectorCacheService.invalidate_item_cache(@item1)

    # Next call should be a cache miss
    call_count = 0
    ::Caching::VectorCacheService.cache_similar_items(@user, @query_vector, limit: 10) do
      call_count += 1
      [ @item1 ]
    end

    assert_equal 1, call_count, "Cache should be invalidated"
  end

  test "cache_stats returns hit rate information" do
    stats = ::Caching::VectorCacheService.cache_stats

    assert stats.key?(:namespace)
    assert stats.key?(:hit_count)
    assert stats.key?(:miss_count)
    assert stats.key?(:hit_rate)
    assert_equal "vector_cache", stats[:namespace]
  end

  test "cache_similar_items handles nil user gracefully" do
    results = ::Caching::VectorCacheService.cache_similar_items(nil, @query_vector, limit: 10) do
      []
    end

    assert_equal 0, results.count
  end

  test "cache_similar_items handles nil vector gracefully" do
    results = ::Caching::VectorCacheService.cache_similar_items(@user, nil, limit: 10) do
      [ @item1 ]
    end

    assert_equal 0, results.count
  end
end
