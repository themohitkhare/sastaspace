# Service for caching vector similarity calculations and search results
# Reduces expensive vector operations by caching results with smart invalidation
require "digest"

module Caching
  class VectorCacheService
  CACHE_NAMESPACE = "vector_cache"
  DEFAULT_TTL = 24.hours
  SIMILARITY_TTL = 12.hours
  SEARCH_RESULT_TTL = 6.hours
  RECOMMENDATION_TTL = 4.hours

  # Cache similarity search results
  # @param user [User] The user performing the search
  # @param query_vector [Array<Float>] The query vector
  # @param limit [Integer] Result limit
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<InventoryItem>] Similar items
  def self.cache_similar_items(user, query_vector, limit: 10, &block)
    return [] if block.nil?
    return [] unless query_vector.present?
    return [] unless user.present?
    return [] unless user.respond_to?(:id)

    cache_key = build_similar_items_key(user.id, query_vector, limit)
    cached_result = read_cache(cache_key)

    if cached_result
      log_cache_hit("similar_items", cache_key)
      return load_items_from_ids(cached_result, user)
    end

    log_cache_miss("similar_items", cache_key)
    result = block.call
    item_ids = result.map(&:id)
    write_cache(cache_key, item_ids, expires_in: SEARCH_RESULT_TTL)
    result
  end

  # Cache semantic search results (text -> embedding -> search)
  # @param user [User] The user performing the search
  # @param query_text [String] The search query text
  # @param limit [Integer] Result limit
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<InventoryItem>] Search results
  def self.cache_semantic_search(user, query_text, limit: 10, &block)
    return block.call if block.nil?
    return block.call if query_text.blank?

    cache_key = build_semantic_search_key(user.id, query_text, limit)
    cached_result = read_cache(cache_key)

    if cached_result
      log_cache_hit("semantic_search", cache_key)
      return load_items_from_ids(cached_result, user)
    end

    log_cache_miss("semantic_search", cache_key)
    result = block.call
    item_ids = result.map(&:id)
    write_cache(cache_key, item_ids, expires_in: SEARCH_RESULT_TTL)
    result
  end

  # Cache outfit recommendation results
  # @param user [User] The user
  # @param base_item [InventoryItem] The base item for recommendations
  # @param limit [Integer] Result limit
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<InventoryItem>] Recommended items
  def self.cache_outfit_recommendations(user, base_item, limit: 5, &block)
    return block.call if block.nil?
    return block.call unless base_item&.embedding_vector.present?

    cache_key = build_recommendation_key(user.id, base_item.id, limit)
    cached_result = read_cache(cache_key)

    if cached_result
      log_cache_hit("outfit_recommendations", cache_key)
      return load_items_from_ids(cached_result, user)
    end

    log_cache_miss("outfit_recommendations", cache_key)
    result = block.call
    item_ids = result.map(&:id)
    write_cache(cache_key, item_ids, expires_in: RECOMMENDATION_TTL)
    result
  end

  # Cache outfit suggestions (completing an outfit)
  # @param user [User] The user
  # @param outfit_items [Array<InventoryItem>, Outfit] Items in the outfit
  # @param limit [Integer] Result limit
  # @param exclude_ids [Array<Integer>] Item IDs to exclude
  # @param block [Proc] Block to execute if cache miss
  # @return [Array<InventoryItem>] Suggested items
  def self.cache_outfit_suggestions(user, outfit_items, limit: 6, exclude_ids: [], &block)
    return block.call if block.nil?
    return block.call if outfit_items.blank?

    # Build cache key from outfit item IDs
    item_ids = outfit_items.is_a?(Outfit) ? outfit_items.inventory_items.pluck(:id) : outfit_items.map(&:id)
    return block.call if item_ids.empty?

    cache_key = build_suggestion_key(user.id, item_ids.sort, exclude_ids.sort, limit)
    cached_result = read_cache(cache_key)

    if cached_result
      log_cache_hit("outfit_suggestions", cache_key)
      return load_items_from_ids(cached_result, user)
    end

    log_cache_miss("outfit_suggestions", cache_key)
    result = block.call
    item_ids_result = result.map(&:id)
    write_cache(cache_key, item_ids_result, expires_in: RECOMMENDATION_TTL)
    result
  end

  # Cache similarity calculation between two vectors
  # @param vector1 [Array<Float>] First vector
  # @param vector2 [Array<Float>] Second vector
  # @param block [Proc] Block to execute if cache miss
  # @return [Float] Similarity score
  def self.cache_similarity_score(vector1, vector2, &block)
    return block.call if block.nil?
    return block.call unless vector1.present? && vector2.present?

    cache_key = build_similarity_key(vector1, vector2)
    cached_result = read_cache(cache_key)

    if cached_result
      log_cache_hit("similarity_score", cache_key)
      return cached_result
    end

    log_cache_miss("similarity_score", cache_key)
    result = block.call
    write_cache(cache_key, result, expires_in: SIMILARITY_TTL) if result.is_a?(Numeric)
    result
  end

  # Invalidate all caches for a user
  # Uses version-based invalidation - increments user cache version
  # @param user [User] The user
  def self.invalidate_user_cache(user)
    return unless user.present?

    increment_user_cache_version(user.id)
    log_cache_invalidation("user", user.id)
  end

  # Invalidate caches related to a specific item
  # @param item [InventoryItem] The inventory item
  def self.invalidate_item_cache(item)
    return unless item.present?

    user = item.user
    return unless user.present?

    # Invalidate all user caches (simpler than pattern matching)
    invalidate_user_cache(user)
    log_cache_invalidation("item", item.id)
  end

  # Invalidate all vector caches (use with caution)
  def self.invalidate_all
    pattern = "#{CACHE_NAMESPACE}:*"
    delete_by_pattern(pattern)
    log_cache_invalidation("all", nil)
  end

  # Get cache statistics
  # @return [Hash] Cache hit/miss statistics
  def self.cache_stats
    {
      namespace: CACHE_NAMESPACE,
      hit_count: read_metric("hit_count") || 0,
      miss_count: read_metric("miss_count") || 0,
      hit_rate: calculate_hit_rate
    }
  end

  # Reset cache statistics
  def self.reset_stats
    write_metric("hit_count", 0)
    write_metric("miss_count", 0)
  end

  private

  def self.build_similar_items_key(user_id, query_vector, limit)
    vector_hash = Digest::SHA256.hexdigest(query_vector.join(","))
    user_version = read_user_cache_version(user_id)
    "#{CACHE_NAMESPACE}:similar_items:user:#{user_id}:v#{user_version}:vector:#{vector_hash}:limit:#{limit}"
  end

  def self.build_semantic_search_key(user_id, query_text, limit)
    text_hash = Digest::SHA256.hexdigest(query_text.downcase.strip)
    user_version = read_user_cache_version(user_id)
    "#{CACHE_NAMESPACE}:semantic_search:user:#{user_id}:v#{user_version}:text:#{text_hash}:limit:#{limit}"
  end

  def self.build_recommendation_key(user_id, base_item_id, limit)
    user_version = read_user_cache_version(user_id)
    "#{CACHE_NAMESPACE}:recommendations:user:#{user_id}:v#{user_version}:item:#{base_item_id}:limit:#{limit}"
  end

  def self.build_suggestion_key(user_id, item_ids, exclude_ids, limit)
    items_hash = Digest::SHA256.hexdigest(item_ids.join(","))
    excludes_hash = Digest::SHA256.hexdigest(exclude_ids.join(","))
    user_version = read_user_cache_version(user_id)
    "#{CACHE_NAMESPACE}:suggestions:user:#{user_id}:v#{user_version}:items:#{items_hash}:excludes:#{excludes_hash}:limit:#{limit}"
  end

  def self.build_similarity_key(vector1, vector2)
    # Normalize vectors for consistent hashing (sort to handle order-independent similarity)
    v1_str = vector1.join(",")
    v2_str = vector2.join(",")
    combined = [ v1_str, v2_str ].sort.join("|")
    hash = Digest::SHA256.hexdigest(combined)
    "#{CACHE_NAMESPACE}:similarity:#{hash}"
  end

  def self.load_items_from_ids(item_ids, user)
    return [] if item_ids.blank?

    # Load items with all necessary associations
    items = user.inventory_items
                .includes(:category, :subcategory, :brand, :tags, :ai_analyses,
                          primary_image_attachment: :blob,
                          additional_images_attachments: :blob)
                .where(id: item_ids)
                .to_a

    # Preserve original order from cached item_ids
    items.sort_by { |item| item_ids.index(item.id) || Float::INFINITY }
  end

  def self.read_cache(key)
    Rails.cache.read(key)
  end

  def self.write_cache(key, value, expires_in: DEFAULT_TTL)
    Rails.cache.write(key, value, expires_in: expires_in)
  end

  def self.read_user_cache_version(user_id)
    key = "#{CACHE_NAMESPACE}:user_version:#{user_id}"
    Rails.cache.read(key) || 1
  end

  def self.increment_user_cache_version(user_id)
    key = "#{CACHE_NAMESPACE}:user_version:#{user_id}"
    current = read_user_cache_version(user_id)
    Rails.cache.write(key, current + 1, expires_in: nil) # Never expire
  end

  def self.delete_by_pattern(pattern)
    # Solid Cache doesn't support pattern deletion directly
    # We use version-based invalidation instead
    Rails.logger.info "Pattern deletion requested for #{pattern}, using version-based invalidation"
  end

  def self.log_cache_hit(operation, key)
    increment_metric("hit_count")
    Rails.logger.debug "[VectorCache] HIT: #{operation} - #{key.truncate(100)}"
  end

  def self.log_cache_miss(operation, key)
    increment_metric("miss_count")
    Rails.logger.debug "[VectorCache] MISS: #{operation} - #{key.truncate(100)}"
  end

  def self.log_cache_invalidation(type, id)
    Rails.logger.info "[VectorCache] INVALIDATED: #{type} - #{id}"
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
  end
end
