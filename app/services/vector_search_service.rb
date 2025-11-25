class VectorSearchService
  def self.find_similar_items(user, query_vector, limit: 10)
    return [] unless query_vector.present?

    # Validate and sanitize vector input
    validated_vector = validate_and_sanitize_vector(query_vector)
    return [] unless validated_vector

    # Use caching to avoid expensive vector calculations
    Caching::VectorCacheService.cache_similar_items(user, validated_vector, limit: limit) do
      # Use parameterized query to prevent SQL injection
      vector_str = format_vector_string(validated_vector)
      escaped_vector = ActiveRecord::Base.connection.quote(vector_str)

      user.inventory_items
          .includes(:category, :subcategory, :brand, :tags, :ai_analyses,
                    primary_image_attachment: :blob,
                    additional_images_attachments: :blob)
          .where.not(embedding_vector: nil)
          .order(Arel.sql("embedding_vector <-> #{escaped_vector}::vector"))
          .limit(limit)
          .to_a
    end
  end

  def self.semantic_search(user, query_text, limit: 10)
    return [] if query_text.blank?

    # Use caching for semantic search (text -> embedding -> search)
    Caching::VectorCacheService.cache_semantic_search(user, query_text, limit: limit) do
      # Generate embedding from text using the embedding service (also cached)
      query_vector = EmbeddingService.generate_text_embedding(query_text)

      return [] unless query_vector.present?

      find_similar_items(user, query_vector, limit: limit)
    end
  end

  def self.find_items_by_image_similarity(user, image_vector, limit: 10)
    return [] unless image_vector.present?

    # Validate and sanitize vector input
    validated_vector = validate_and_sanitize_vector(image_vector)
    return [] unless validated_vector

    # Use caching for image similarity searches
    Caching::VectorCacheService.cache_similar_items(user, validated_vector, limit: limit) do
      # Use parameterized query to prevent SQL injection
      vector_str = format_vector_string(validated_vector)
      escaped_vector = ActiveRecord::Base.connection.quote(vector_str)

      user.inventory_items
          .includes(:category, :subcategory, :brand, :tags, :ai_analyses,
                    primary_image_attachment: :blob,
                    additional_images_attachments: :blob)
          .where.not(embedding_vector: nil)
          .order(Arel.sql("embedding_vector <-> #{escaped_vector}::vector"))
          .limit(limit)
          .to_a
    end
  end

  def self.recommend_outfit_items(user, base_item, limit: 5)
    return [] unless base_item.embedding_vector.present?

    # Use caching for outfit recommendations
    Caching::VectorCacheService.cache_outfit_recommendations(user, base_item, limit: limit) do
      # Find similar items that could work in an outfit
      similar_items = find_similar_items(user, base_item.embedding_vector, limit: limit * 2)

      # Filter by complementary categories (e.g., if base is top, find bottoms)
      complementary_items = similar_items.select do |item|
        complementary_category?(base_item.category.name, item.category.name)
      end

      complementary_items.first(limit)
    end
  end

  # Suggest items to complete or enhance an outfit
  # Takes an outfit (or array of inventory items) and suggests complementary items
  def self.suggest_outfit_items(user, outfit_items, limit: 6, exclude_ids: [])
    return [] if outfit_items.blank?

    # Convert outfit to array of inventory items if needed
    items = outfit_items.is_a?(Outfit) ? outfit_items.inventory_items.to_a : Array(outfit_items)
    return [] if items.empty?

    # Get item IDs to exclude (items already in outfit)
    excluded_item_ids = (exclude_ids + items.map(&:id)).uniq

      # Note: We can't use the standard cache here because we need to return enriched data
      # (match_score, reasoning, badges), not just items. Cache will be handled differently.
      # For now, skip caching to avoid breaking the structure - can optimize later
      # Caching::VectorCacheService.cache_outfit_suggestions(user, outfit_items, limit: limit, exclude_ids: excluded_item_ids) do
      # Analyze existing outfit to determine what's missing
      existing_categories = items.map { |item| item.category&.name&.downcase }.compact
      existing_category_names = items.map { |item| item.category&.name }.compact

      suggestions = []

      # Strategy 1: Find complementary items for each existing item
      items.each do |item|
        next unless item.embedding_vector.present?

        # Find similar items using vector search (already cached)
        similar = find_similar_items(user, item.embedding_vector, limit: limit * 2)
          .reject { |s| excluded_item_ids.include?(s.id) }

        # Score and filter by complementary categories
        similar.each do |candidate|
          category_name = candidate.category&.name&.downcase || ""

          # Skip if same category (already have this type)
          next if existing_categories.include?(category_name)

          # Boost score if complementary category
          score = complementary_category?(item.category&.name, candidate.category&.name) ? 2.0 : 1.0

          # Add to suggestions with score (deduplicate by item id)
          existing = suggestions.find { |s| s[:item].id == candidate.id }
          if existing
            existing[:score] += score
          else
            suggestions << {
              item: candidate,
              score: score,
              reason: get_suggestion_reason(item, candidate, existing_category_names)
            }
          end
        end
      end

      # Strategy 2: Find items that are commonly needed but missing
      missing_categories = identify_missing_categories(existing_category_names)
      if missing_categories.any?
        missing_categories.each do |category_name|
          category = Category.find_by("LOWER(name) = ?", category_name.downcase)
          next unless category

          category_items = user.inventory_items
                             .includes(:category, :subcategory, :brand, :tags, :ai_analyses,
                                       primary_image_attachment: :blob,
                                       additional_images_attachments: :blob)
                             .where(category: category)
                             .where.not(id: excluded_item_ids)
                             .where.not(embedding_vector: nil)
                             .limit(limit)

          category_items.each do |candidate|
            # Calculate similarity to outfit's style (average of existing item vectors)
            style_score = calculate_style_similarity(items, candidate)

            existing = suggestions.find { |s| s[:item].id == candidate.id }
            if existing
              existing[:score] += style_score + 1.5 # Boost for missing category
            else
              suggestions << {
                item: candidate,
                score: style_score + 1.5,
                reason: "Completes your outfit - #{category_name}"
              }
            end
          end
        end
      end

      # Sort by score (highest first) and normalize scores
      sorted_suggestions = suggestions.sort_by { |s| -s[:score] }.first(limit)

      # Normalize scores to 0-1 range and add enhanced reasoning
      max_score = sorted_suggestions.first&.dig(:score) || 1.0
      sorted_suggestions.map do |suggestion|
        normalized_score = max_score > 0 ? (suggestion[:score] / max_score).round(2) : 0.0
        # Clamp between 0 and 1
        normalized_score = [ 0.0, [ 1.0, normalized_score ].min ].max

        # Build enhanced reasoning
        reasoning = build_enhanced_reasoning(
          suggestion[:item],
          suggestion[:reason],
          items,
          existing_category_names,
          suggestion[:score],
          normalized_score
        )

        # Determine badges (missing_categories is in outer scope)
        badges = determine_badges(normalized_score, suggestion[:item], existing_category_names, missing_categories)

        {
          item: suggestion[:item],
          match_score: normalized_score,
          reasoning: reasoning,
          badges: badges
        }
      end
    # end  # End of cache block (commented out for now)
  end

  private

  def self.complementary_category?(base_category, candidate_category)
    return false unless base_category.present? && candidate_category.present?

    base_name = base_category.to_s.downcase
    candidate_name = candidate_category.to_s.downcase

    # Define complementary relationships
    complements = {
      "tops" => [ "bottoms", "jeans", "pants", "skirts", "shorts" ],
      "t-shirts" => [ "jeans", "pants", "skirts", "shorts" ],
      "shirts" => [ "jeans", "pants", "skirts" ],
      "bottoms" => [ "tops", "t-shirts", "shirts", "blouses" ],
      "jeans" => [ "tops", "t-shirts", "shirts" ],
      "pants" => [ "tops", "t-shirts", "shirts" ],
      "skirts" => [ "tops", "t-shirts", "shirts", "blouses" ],
      "dresses" => [ "shoes", "boots", "sneakers", "accessories", "bags", "jewelry" ],
      "shoes" => [ "dresses", "bottoms", "jeans", "pants", "skirts" ],
      "boots" => [ "dresses", "jeans", "pants", "skirts" ],
      "sneakers" => [ "jeans", "pants", "shorts", "tops", "t-shirts" ],
      "accessories" => [ "dresses", "tops", "shirts" ],
      "bags" => [ "dresses", "outfits" ],
      "jewelry" => [ "dresses", "tops", "shirts" ]
    }

    complements[base_name]&.include?(candidate_name) || false
  end

  def self.identify_missing_categories(existing_categories)
    missing = []
    existing_lower = existing_categories.map(&:downcase)

    # Check for essential categories
    essential_patterns = {
      top: [ "top", "shirt", "blouse", "t-shirt", "sweater" ],
      bottom: [ "bottom", "jean", "pant", "skirt", "short" ],
      shoe: [ "shoe", "boot", "sneaker", "sandal" ]
    }

    essential_patterns.each do |type, patterns|
      has_type = existing_lower.any? { |cat| patterns.any? { |pattern| cat.include?(pattern) } }
      missing << type.to_s unless has_type
    end

    missing
  end

  def self.calculate_style_similarity(outfit_items, candidate_item)
    return 0.0 unless candidate_item.embedding_vector.present?

    # Calculate average vector of outfit items that have vectors
    vectors_with_embeddings = outfit_items.select { |item| item.embedding_vector.present? }
    return 0.0 if vectors_with_embeddings.empty?

    # Simple average of vectors (for style matching)
    avg_vector = vectors_with_embeddings.map(&:embedding_vector).transpose.map { |x| x.reduce(:+) / x.size.to_f }

    # Calculate cosine similarity (simplified - just use VectorSearchService)
    # This will use caching via find_similar_items
    similar = find_similar_items(vectors_with_embeddings.first.user, avg_vector, limit: 20)

    # Find rank of candidate in similar items
    rank = similar.index(candidate_item)
    return 0.0 unless rank

    # Higher score for better matches (lower rank = better match)
    1.0 / (rank + 1)
  end

  def self.get_suggestion_reason(base_item, candidate_item, existing_categories)
    base_cat = base_item.category&.name || "item"
    candidate_cat = candidate_item.category&.name || "item"

    if complementary_category?(base_cat, candidate_cat)
      "Pairs well with #{base_cat}"
    elsif existing_categories.include?(candidate_cat)
      "Similar style to your #{candidate_cat}"
    else
      "Complements your outfit"
    end
  end

  def self.build_enhanced_reasoning(candidate_item, base_reason, outfit_items, existing_categories, raw_score, match_score)
    tags = []
    primary_reason = "Style match"
    details = base_reason

    # Analyze color coordination
    candidate_color = candidate_item.color || candidate_item.metadata&.dig("color")
    outfit_colors = outfit_items.map { |item| item.color || item.metadata&.dig("color") }.compact

    if candidate_color.present? && outfit_colors.any?
      # Check for color coordination
      if outfit_colors.include?(candidate_color)
        tags << "similar_color"
        primary_reason = "Color coordination"
        details = "Matches the #{candidate_color} in your outfit"
      elsif ColorCoordinationService.normalize_colors(candidate_color).any? { |c| ColorCoordinationService.normalize_colors(outfit_colors.first).include?(c) }
        tags << "complementary_color"
        primary_reason = "Color coordination"
        details = "Complements your #{outfit_colors.first} items"
      end
    end

    # Check for style consistency
    candidate_category = candidate_item.category&.name&.downcase || ""
    if existing_categories.map(&:downcase).include?(candidate_category)
      tags << "style_match"
      primary_reason = "Style consistency" unless tags.include?("similar_color")
      details = "Matches your #{candidate_item.category&.name} style"
    end

    # Check for complementary category
    outfit_items.each do |outfit_item|
      if complementary_category?(outfit_item.category&.name, candidate_item.category&.name)
        tags << "complementary_style"
        primary_reason = "Perfect pairing" unless tags.include?("similar_color")
        details = "Pairs perfectly with your #{outfit_item.category&.name}"
        break
      end
    end

    # Check for occasion appropriateness (if outfit has occasion metadata)
    # This is a placeholder - can be enhanced with actual occasion analysis
    tags << "occasion_appropriate" if match_score > 0.7

    # Fallback to base reason if no specific reason found
    if primary_reason == "Style match" && details == base_reason
      details = base_reason
    end

    {
      primary: primary_reason,
      details: details,
      tags: tags.uniq
    }
  end

  def self.determine_badges(match_score, candidate_item, existing_categories, missing_categories)
    badges = []

    # Best match badge (top 20% match score)
    badges << "best_match" if match_score >= 0.8

    # Completes outfit badge (fills missing category type)
    candidate_category = candidate_item.category&.name&.downcase || ""
    if missing_categories.any?
      # Check if candidate matches any missing category type
      missing_categories.each do |missing_type|
        # missing_type is like "top", "bottom", "shoe"
        # Check if candidate category name includes the missing type
        category_patterns = {
          "top" => [ "top", "shirt", "blouse", "t-shirt", "sweater" ],
          "bottom" => [ "bottom", "jean", "pant", "skirt", "short" ],
          "shoe" => [ "shoe", "boot", "sneaker", "sandal" ]
        }

        patterns = category_patterns[missing_type.downcase] || []
        if patterns.any? { |pattern| candidate_category.include?(pattern) }
          badges << "completes_outfit"
          break
        end
      end
    end

    # Trending badge (high wear count indicates popularity)
    if candidate_item.respond_to?(:wear_count) && candidate_item.wear_count.to_i > 5
      badges << "trending"
    end

    badges
  end

  # Validate and sanitize vector input to prevent SQL injection
  # Returns validated array of numbers or nil if invalid
  def self.validate_and_sanitize_vector(vector)
    return nil unless vector.is_a?(Array)
    return nil if vector.empty?

    # Convert all elements to floats and validate they're numeric
    validated = vector.map do |v|
      # Convert to float, raise error if not numeric
      Float(v)
    rescue ArgumentError, TypeError
      return nil # Invalid non-numeric value
    end

    # Ensure reasonable bounds to prevent extremely large values
    validated.each do |val|
      return nil if val.infinite? || val.nan?
      return nil if val.abs > 1_000_000 # Reasonable bound for vector components
    end

    validated
  end

  # Format vector array as PostgreSQL vector string format: [1.0,2.0,3.0]
  def self.format_vector_string(vector)
    "[#{vector.join(',')}]"
  end
end
