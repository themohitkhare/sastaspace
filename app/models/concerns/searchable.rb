# Concern for vector search functionality
module Searchable
  extend ActiveSupport::Concern

  included do
    # Scope-based approach for direct vector search - using parameterized queries
    scope :similar_to, ->(vector, limit: 10) {
      # Validate and sanitize vector input
      validated_vector = VectorSearchService.validate_and_sanitize_vector(vector)
      next where("1=0") unless validated_vector # Return empty result if invalid

      # Use parameterized query to prevent SQL injection
      vector_str = VectorSearchService.format_vector_string(validated_vector)
      escaped_vector = ActiveRecord::Base.connection.quote(vector_str)

      where.not(embedding_vector: nil)
           .order(Arel.sql("embedding_vector <-> #{escaped_vector}::vector"))
           .limit(limit)
    }
  end

  # Find similar items using vector search
  def similar_items(limit: 5)
    return [] unless embedding_vector.present?

    # Validate and sanitize vector input
    validated_vector = VectorSearchService.validate_and_sanitize_vector(embedding_vector)
    return [] unless validated_vector

    # Use parameterized query to prevent SQL injection
    vector_str = VectorSearchService.format_vector_string(validated_vector)
    escaped_vector = ActiveRecord::Base.connection.quote(vector_str)

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(id: id)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> #{escaped_vector}::vector"))
        .limit(limit)
  end

  def find_similar_items(limit: 10)
    return [] unless embedding_vector.present?

    # Validate and sanitize vector input
    validated_vector = VectorSearchService.validate_and_sanitize_vector(embedding_vector)
    return [] unless validated_vector

    # Use parameterized query to prevent SQL injection
    vector_str = VectorSearchService.format_vector_string(validated_vector)
    escaped_vector = ActiveRecord::Base.connection.quote(vector_str)

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(id: id)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> #{escaped_vector}::vector"))
        .limit(limit)
  end
end
