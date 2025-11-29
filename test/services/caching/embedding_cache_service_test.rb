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
    mock_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

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
    embedding1 = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.1 }
    embedding2 = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.2 }

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
    mock_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

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
    mock_embedding1 = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.1 }
    mock_embedding2 = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.2 }

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
      Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.1 }
    end

    assert_nil result
  end

  test "cache_item_embedding handles nil item gracefully" do
    result = ::Caching::EmbeddingCacheService.cache_item_embedding(nil) do
      Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.1 }
    end

    assert_nil result
  end

  test "cache_text_embedding rejects embeddings with wrong dimensions" do
    # Try to cache an embedding with wrong dimensions (768 instead of 1024)
    invalid_embedding = Array.new(768) { rand(-1.0..1.0) }

    call_count = 0
    result = ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      invalid_embedding
    end

    # Should return the invalid embedding (caller handles it)
    assert_equal invalid_embedding, result
    assert_equal 1, call_count

    # But it should NOT be cached
    call_count = 0
    result2 = ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      invalid_embedding
    end

    # Should be called again because invalid embedding wasn't cached
    assert_equal 1, call_count, "Invalid embedding should not be cached"
  end

  test "cache_text_embedding invalidates cached embeddings with wrong dimensions" do
    # First, cache a valid embedding
    valid_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

    call_count = 0
    ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      valid_embedding
    end

    assert_equal 1, call_count

    # Manually cache an invalid embedding (simulating old cached data)
    cache_key = ::Caching::EmbeddingCacheService.send(:build_text_embedding_key, @text)
    invalid_embedding = Array.new(768) { rand(-1.0..1.0) }
    Rails.cache.write(cache_key, invalid_embedding)

    # Next call should detect invalid dimensions and regenerate
    new_valid_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { 0.5 }
    result = ::Caching::EmbeddingCacheService.cache_text_embedding(@text) do
      call_count += 1
      new_valid_embedding
    end

    # Should have been called again because invalid cache was detected
    assert_equal 2, call_count, "Should regenerate when invalid cached embedding detected"
    assert_equal new_valid_embedding, result
  end

  test "cache_item_embedding rejects embeddings with wrong dimensions" do
    # Try to cache an embedding with wrong dimensions
    invalid_embedding = Array.new(768) { rand(-1.0..1.0) }

    call_count = 0
    result = ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      invalid_embedding
    end

    # Should return the invalid embedding (caller handles it)
    assert_equal invalid_embedding, result
    assert_equal 1, call_count

    # But it should NOT be cached
    call_count = 0
    result2 = ::Caching::EmbeddingCacheService.cache_item_embedding(@item) do
      call_count += 1
      invalid_embedding
    end

    # Should be called again because invalid embedding wasn't cached
    assert_equal 1, call_count, "Invalid embedding should not be cached"
  end

  test "validate_embedding_dimensions accepts valid embeddings" do
    valid_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }
    assert ::Caching::EmbeddingCacheService.send(:validate_embedding_dimensions, valid_embedding)
  end

  test "validate_embedding_dimensions rejects wrong dimensions" do
    invalid_embedding = Array.new(768) { rand(-1.0..1.0) }
    assert_not ::Caching::EmbeddingCacheService.send(:validate_embedding_dimensions, invalid_embedding)
  end

  test "validate_embedding_dimensions rejects non-array" do
    assert_not ::Caching::EmbeddingCacheService.send(:validate_embedding_dimensions, "not an array")
    assert_not ::Caching::EmbeddingCacheService.send(:validate_embedding_dimensions, nil)
  end

  test "validate_embedding_dimensions rejects array with non-numeric values" do
    invalid_embedding = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { "not a number" }
    assert_not ::Caching::EmbeddingCacheService.send(:validate_embedding_dimensions, invalid_embedding)
  end
end
