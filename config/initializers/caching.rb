# Caching configuration for vector operations and embeddings
# Provides centralized configuration and monitoring for cache strategies

Rails.application.config.after_initialize do
  # Log cache configuration on startup
  cache_store = Rails.cache.class.name
  Rails.logger.info "[CacheConfig] Using cache store: #{cache_store}"

  # Verify cache is working
  test_key = "cache_test_#{SecureRandom.hex(4)}"
  Rails.cache.write(test_key, "test", expires_in: 1.second)
  if Rails.cache.read(test_key) == "test"
    Rails.logger.info "[CacheConfig] ✓ Cache store is operational"
  else
    Rails.logger.warn "[CacheConfig] ⚠ Cache store may not be working correctly"
  end
  Rails.cache.delete(test_key)

  # Initialize cache statistics if needed
  unless Rails.env.test?
    # Reset stats on application restart (optional - comment out to preserve stats)
    # VectorCacheService.reset_stats
    # EmbeddingCacheService.reset_stats

    # Log current cache statistics
    vector_stats = Caching::VectorCacheService.cache_stats
    embedding_stats = Caching::EmbeddingCacheService.cache_stats

    Rails.logger.info "[CacheConfig] Vector cache stats: #{vector_stats[:hit_rate]}% hit rate (#{vector_stats[:hit_count]} hits, #{vector_stats[:miss_count]} misses)"
    Rails.logger.info "[CacheConfig] Embedding cache stats: #{embedding_stats[:hit_rate]}% hit rate (#{embedding_stats[:hit_count]} hits, #{embedding_stats[:miss_count]} misses)"
  end
end

# Cache warming strategies (can be called from rake tasks or background jobs)
module CacheWarming
  # Warm cache for popular items
  def self.warm_popular_items(limit: 100)
    Rails.logger.info "[CacheWarming] Warming cache for #{limit} popular items"

    InventoryItem.includes(:user, :category, :brand, :ai_analyses)
                 .where.not(embedding_vector: nil)
                 .order(wear_count: :desc, created_at: :desc)
                 .limit(limit)
                 .find_each do |item|
      # Pre-generate embeddings if missing
      if item.embedding_vector.nil?
        EmbeddingService.generate_for_item(item)
      end

      # Pre-cache similar items
      VectorSearchService.find_similar_items(item.user, item.embedding_vector, limit: 10)
    end

    Rails.logger.info "[CacheWarming] ✓ Cache warming completed"
  end

  # Warm cache for active users
  def self.warm_active_users(limit: 50)
    Rails.logger.info "[CacheWarming] Warming cache for #{limit} active users"

    User.joins(:inventory_items)
        .group("users.id")
        .having("COUNT(inventory_items.id) > ?", 10)
        .order("COUNT(inventory_items.id) DESC")
        .limit(limit)
        .find_each do |user|
      # Pre-cache semantic searches for common queries
      common_queries = [ "blue shirt", "jeans", "dress", "shoes", "jacket" ]
      common_queries.each do |query|
        VectorSearchService.semantic_search(user, query, limit: 10)
      end
    end

    Rails.logger.info "[CacheWarming] ✓ Cache warming completed"
  end
end
