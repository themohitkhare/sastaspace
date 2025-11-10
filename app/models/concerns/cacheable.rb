# Concern for automatic cache invalidation on model updates
# Ensures vector and embedding caches are invalidated when data changes
module Cacheable
  extend ActiveSupport::Concern

  included do
    # Invalidate caches after updates that affect vector operations
    after_update :invalidate_vector_caches, if: :should_invalidate_cache?
    after_destroy :invalidate_vector_caches
  end

  private

  def should_invalidate_cache?
    # For InventoryItem: invalidate if any attribute that affects embeddings or vector search changed
    if is_a?(InventoryItem)
      cache_relevant_attributes = %w[
        name item_type category_id subcategory_id brand_id
        metadata embedding_vector
      ]
      return cache_relevant_attributes.any? { |attr| saved_change_to_attribute?(attr) }
    end

    # For Outfit: invalidate if outfit items changed (affects recommendations)
    if is_a?(Outfit)
      return saved_change_to_attribute?(:name) || outfit_items_changed?
    end

    false
  end

  def invalidate_vector_caches
    # Invalidate item-specific caches
    if is_a?(InventoryItem) && user.present?
      Caching::VectorCacheService.invalidate_item_cache(self)
      Caching::EmbeddingCacheService.invalidate_item_embedding(self)
    end

    # Invalidate outfit-related caches
    if is_a?(Outfit) && user.present?
      Caching::VectorCacheService.invalidate_user_cache(user)
    end
  end

  def outfit_items_changed?
    # Check if outfit_items association changed
    return false unless is_a?(Outfit)

    # This will be triggered when outfit_items are added/removed
    # We can't easily detect this in after_update, so we'll invalidate on any outfit update
    # A more sophisticated approach would use after_commit with association callbacks
    true
  end
end
