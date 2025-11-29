# Service for caching AI-generated embeddings
# Reduces expensive Ollama API calls by caching embedding results
require "digest"

module Caching
  class EmbeddingCacheService
  CACHE_NAMESPACE = "embedding_cache"
  DEFAULT_TTL = 7.days
  TEXT_EMBEDDING_TTL = 7.days
  ITEM_EMBEDDING_TTL = 30.days # Item embeddings change less frequently

  # Cache text embedding generation
  # @param text [String] The text to embed
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<Float>] Embedding vector
  def self.cache_text_embedding(text, &block)
    return nil if block.nil?
    return nil if text.blank?

    cache_key = build_text_embedding_key(text)
    cached_result = read_cache(cache_key)

    if cached_result
      # Validate cached embedding dimensions before returning
      if validate_embedding_dimensions(cached_result)
        log_cache_hit("text_embedding", cache_key)
        return cached_result
      else
        # Cached embedding has wrong dimensions, invalidate and regenerate
        Rails.logger.warn "[EmbeddingCache] Invalid cached embedding dimensions, invalidating cache for: #{cache_key.truncate(100)}"
        delete_cache(cache_key)
      end
    end

    log_cache_miss("text_embedding", cache_key)
    result = block.call
    # Only cache if result is valid array with correct dimensions
    if result.is_a?(Array) && validate_embedding_dimensions(result)
      write_cache(cache_key, result, expires_in: TEXT_EMBEDDING_TTL)
    end
    result
  end

  # Cache item embedding generation
  # @param inventory_item [InventoryItem] The inventory item
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<Float>] Embedding vector
  def self.cache_item_embedding(inventory_item, &block)
    return nil if block.nil?
    return nil unless inventory_item.present?

    # Use item's description hash as cache key
    # This will invalidate when item properties change
    cache_key = build_item_embedding_key(inventory_item)
    cached_result = read_cache(cache_key)

    if cached_result
      # Validate cached embedding dimensions before returning
      if validate_embedding_dimensions(cached_result)
        log_cache_hit("item_embedding", cache_key)
        return cached_result
      else
        # Cached embedding has wrong dimensions, invalidate and regenerate
        Rails.logger.warn "[EmbeddingCache] Invalid cached embedding dimensions, invalidating cache for: #{cache_key.truncate(100)}"
        delete_cache(cache_key)
      end
    end

    log_cache_miss("item_embedding", cache_key)
    result = block.call
    # Only cache if result is valid array with correct dimensions
    if result.is_a?(Array) && validate_embedding_dimensions(result)
      write_cache(cache_key, result, expires_in: ITEM_EMBEDDING_TTL)
    end
    result
  end

  # Invalidate embedding cache for a specific item
  # @param inventory_item [InventoryItem] The inventory item
  def self.invalidate_item_embedding(inventory_item)
    return unless inventory_item.present?

    cache_key = build_item_embedding_key(inventory_item)
    delete_cache(cache_key)
    log_cache_invalidation("item_embedding", inventory_item.id)
  end

  # Invalidate all text embeddings (use when embedding model changes)
  def self.invalidate_all_text_embeddings
    # We can't easily pattern match, so we'll track version
    increment_model_version
    log_cache_invalidation("all_text_embeddings", nil)
  end

  # Invalidate all embeddings (use with caution)
  def self.invalidate_all
    increment_model_version
    log_cache_invalidation("all_embeddings", nil)
  end

  # Get cache statistics
  # @return [Hash] Cache hit/miss statistics
  def self.cache_stats
    {
      namespace: CACHE_NAMESPACE,
      hit_count: read_metric("hit_count") || 0,
      miss_count: read_metric("miss_count") || 0,
      hit_rate: calculate_hit_rate,
      model_version: read_model_version
    }
  end

  # Reset cache statistics
  def self.reset_stats
    write_metric("hit_count", 0)
    write_metric("miss_count", 0)
  end

  private

  def self.build_text_embedding_key(text)
    # Normalize text: lowercase, strip, and hash
    normalized = text.downcase.strip
    text_hash = Digest::SHA256.hexdigest(normalized)
    model_version = read_model_version
    "#{CACHE_NAMESPACE}:text:#{text_hash}:v#{model_version}"
  end

  def self.build_item_embedding_key(inventory_item)
    # Build a hash from item properties that affect embedding
    # This ensures cache invalidation when item changes
    description_parts = [
      inventory_item.name,
      inventory_item.item_type,
      inventory_item.category&.name,
      inventory_item.brand&.name,
      inventory_item.metadata_summary.to_json
    ]

    # Include latest AI analysis if it exists
    latest_analysis = inventory_item.ai_analyses.order(created_at: :desc).first
    if latest_analysis
      description_parts << latest_analysis.analysis_data_hash.to_json
    end

    description = description_parts.compact.join("|")
    description_hash = Digest::SHA256.hexdigest(description)
    model_version = read_model_version
    "#{CACHE_NAMESPACE}:item:#{inventory_item.id}:#{description_hash}:v#{model_version}"
  end

  def self.read_cache(key)
    Rails.cache.read(key)
  end

  def self.write_cache(key, value, expires_in: DEFAULT_TTL)
    Rails.cache.write(key, value, expires_in: expires_in)
  end

  def self.delete_cache(key)
    Rails.cache.delete(key)
  end

  def self.log_cache_hit(operation, key)
    increment_metric("hit_count")
    Rails.logger.debug "[EmbeddingCache] HIT: #{operation} - #{key.truncate(100)}"
  end

  def self.log_cache_miss(operation, key)
    increment_metric("miss_count")
    Rails.logger.debug "[EmbeddingCache] MISS: #{operation} - #{key.truncate(100)}"
  end

  def self.log_cache_invalidation(type, id)
    Rails.logger.info "[EmbeddingCache] INVALIDATED: #{type} - #{id}"
  end

  def self.increment_metric(metric_name)
    key = "#{CACHE_NAMESPACE}:metrics:#{metric_name}"
    current = read_metric(metric_name) || 0
    write_metric(metric_name, current + 1)
  end

  def self.read_metric(metric_name)
    key = "#{CACHE_NAMESPACE}:metrics:#{metric_name}"
    Rails.cache.read(key) || 0
  end

  def self.write_metric(metric_name, value)
    key = "#{CACHE_NAMESPACE}:metrics:#{metric_name}"
    Rails.cache.write(key, value, expires_in: 7.days)
  end

  def self.calculate_hit_rate
    hits = read_metric("hit_count") || 0
    misses = read_metric("miss_count") || 0
    total = hits + misses
    return 0.0 if total.zero?

    (hits.to_f / total * 100).round(2)
  end

  def self.read_model_version
    key = "#{CACHE_NAMESPACE}:model_version"
    Rails.cache.read(key) || 1
  end

  def self.increment_model_version
    key = "#{CACHE_NAMESPACE}:model_version"
    current = read_model_version
    Rails.cache.write(key, current + 1, expires_in: nil) # Never expire
  end

  # Validate embedding dimensions match expected database schema
  # @param embedding [Array<Float>] The embedding vector to validate
  # @return [Boolean] True if dimensions are valid, false otherwise
  def self.validate_embedding_dimensions(embedding)
    return false unless embedding.is_a?(Array)
    return false unless embedding.all? { |v| v.is_a?(Numeric) }

    expected_dimensions = EmbeddingService::EXPECTED_DIMENSIONS
    actual_dimensions = embedding.length

    if actual_dimensions != expected_dimensions
      Rails.logger.error "[EmbeddingCache] Dimension mismatch: expected #{expected_dimensions}, got #{actual_dimensions}"
      return false
    end

    true
  end
  end
end
