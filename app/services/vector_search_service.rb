class VectorSearchService
  def self.find_similar_items(user, query_vector, limit: 10)
    return [] unless query_vector.present?

    # Use Rails scopes with Arel.sql for proper SQL escaping
    vector_str = "[#{query_vector.join(',')}]"

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> '#{vector_str}'::vector"))
        .limit(limit)
  end

  def self.semantic_search(user, query_text, limit: 10)
    # Generate embedding from text using Ollama
    query_vector = Ollama::EmbeddingGenerator.generate_text_embedding(query_text)

    return [] unless query_vector.present?

    find_similar_items(user, query_vector, limit: limit)
  end

  def self.find_items_by_image_similarity(user, image_vector, limit: 10)
    return [] unless image_vector.present?

    # Use Rails scopes with Arel.sql for proper SQL escaping
    vector_str = "[#{image_vector.join(',')}]"

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> '#{vector_str}'::vector"))
        .limit(limit)
  end

  def self.recommend_outfit_items(user, base_item, limit: 5)
    return [] unless base_item.embedding_vector.present?

    # Find similar items that could work in an outfit
    similar_items = find_similar_items(user, base_item.embedding_vector, limit: limit * 2)

    # Filter by complementary categories (e.g., if base is top, find bottoms)
    complementary_items = similar_items.select do |item|
      complementary_category?(base_item.category.name, item.category.name)
    end

    complementary_items.first(limit)
  end

  private

  def self.complementary_category?(base_category, candidate_category)
    # Define complementary relationships
    complements = {
      "tops" => [ "bottoms", "dresses", "skirts" ],
      "bottoms" => [ "tops", "dresses" ],
      "dresses" => [ "shoes", "accessories" ],
      "shoes" => [ "dresses", "bottoms" ],
      "accessories" => [ "dresses", "tops" ]
    }

    complements[base_category.downcase]&.include?(candidate_category.downcase) || false
  end
end
