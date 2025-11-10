require "test_helper"

# Test class must not be namespaced to avoid Rails autoloading issues
class EmbeddingCacheServiceTest < ActiveSupport::TestCase
  def setup
    # Use memory store for caching tests (test environment uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
    @category = create(:category, name: "tops")
    @brand = create(:brand)

    @item = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Blue T-Shirt",
                   embedding_vector: nil)

    @text = "blue casual shirt"

    # Clear cache before each test
    Rails.cache.clear
    ::Caching::EmbeddingCacheService.reset_stats
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "cache_text_embedding caches and returns cached results" do
    mock_embedding = Array.new(1536) { rand(-1.0..1.0) }

    call_count = 0
    result1 = ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      mock_embedding
    end

    assert_equal 1, call_count, "Block should be called once on cache miss"
    assert_equal mock_embedding, result1

    # Second call - cache hit
    result2 = ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      mock_embedding
    end

    assert_equal 1, call_count, "Block should not be called again on cache hit"
    assert_equal mock_embedding, result2
  end

  test "cache_text_embedding uses different keys for different texts" do
    text1 = "blue shirt"
    text2 = "red shirt"
    embedding1 = Array.new(1536) { 0.1 }
    embedding2 = Array.new(1536) { 0.2 }

    call_count = 0
    ::Caching::EmbeddingCacheService.cache_text_embedding(text1) do
      call_count += 1
      embedding1
    end

    ::Caching::EmbeddingCacheService.cache_text_embedding(text2) do
      call_count += 1
      embedding2
    end

    assert_equal 2, call_count, "Different texts should result in different cache entries"
  end

  test "cache_item_embedding caches item embeddings" do
    mock_embedding = Array.new(1536) { rand(-1.0..1.0) }

    call_count = 0
    result1 = ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      mock_embedding
    end

    assert_equal 1, call_count

    result2 = ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      mock_embedding
    end

    assert_equal 1, call_count, "Should use cached result"
    assert_equal mock_embedding, result2
  end

  test "cache_item_embedding invalidates when item properties change" do
    mock_embedding1 = Array.new(1536) { 0.1 }
    mock_embedding2 = Array.new(1536) { 0.2 }

    # First cache
    call_count = 0
    ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      mock_embedding1
    end

    assert_equal 1, call_count

    # Change item name (affects embedding description)
    @item.update!(name: "Red T-Shirt")

    # Invalidate cache
    ::Caching::EmbeddingCacheService.invalidate_item_embedding(@item)

    # Next call should be a cache miss
    ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      mock_embedding2
    end

    assert_equal 2, call_count, "Cache should be invalidated after item update"
  end

  test "invalidate_all_text_embeddings increments model version" do
    initial_version = ::Caching::EmbeddingCacheService.cache_stats[:model_version]

    ::Caching::EmbeddingCacheService.invalidate_all_text_embeddings

    new_version = ::Caching::EmbeddingCacheService.cache_stats[:model_version]
    assert new_version > initial_version, "Model version should increment"
  end

  test "cache_stats returns hit rate information" do
    stats = ::Caching::EmbeddingCacheService.cache_stats

    assert stats.key?(:namespace)
    assert stats.key?(:hit_count)
    assert stats.key?(:miss_count)
    assert stats.key?(:hit_rate)
    assert stats.key?(:model_version)
    assert_equal "embedding_cache", stats[:namespace]
  end

  test "cache_text_embedding handles nil text gracefully" do
    result = ::Caching::EmbeddingCacheService.cache_text_embedding(nil) do
      Array.new(1536) { 0.1 }
    end

    assert_nil result
  end

  test "cache_item_embedding handles nil item gracefully" do
    result = ::Caching::EmbeddingCacheService.cache_item_embedding(nil) do
      Array.new(1536) { 0.1 }
    end

    assert_nil result
  end
end
