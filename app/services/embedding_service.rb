class EmbeddingService
  # Generate embedding for an inventory item
  # Results are cached based on item properties to avoid regeneration
  def self.generate_for_item(inventory_item)
    return nil unless inventory_item.present?

    # Use caching for item embeddings (longer TTL since items change less frequently)
    Caching::EmbeddingCacheService.cache_item_embedding(inventory_item) do
      description = build_item_description(inventory_item)
      generate_text_embedding(description)
    end
  end

  # Generate embedding from text directly using RubyLLM with Ollama
  # Results are cached to avoid expensive API calls
  def self.generate_text_embedding(text)
    return nil if text.blank?

    # Use caching to avoid expensive Ollama API calls
    Caching::EmbeddingCacheService.cache_text_embedding(text) do
      begin
        Rails.logger.info "Generating embedding for text: #{text.truncate(100)}"

        embedding = RubyLLM.embed(
          text,
          model: "mxbai-embed-large:latest",
          provider: :ollama,
          assume_model_exists: true
        )

        if embedding&.vectors
          Rails.logger.info "✓ Generated embedding with #{embedding.vectors.length} dimensions"
          embedding.vectors
        else
          Rails.logger.warn "Failed to generate embedding, falling back to placeholder"
          Array.new(1024) { rand(-1.0..1.0) }
        end
      rescue StandardError => e
        Rails.logger.error "Error generating embedding: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n") if e.backtrace
        Array.new(1024) { rand(-1.0..1.0) }
      end
    end
  end

  private

  def self.build_item_description(inventory_item)
    parts = []

    parts << inventory_item.name
    parts << inventory_item.item_type
    parts << inventory_item.category.name if inventory_item.category
    parts << inventory_item.brand.name if inventory_item.brand

    metadata = inventory_item.metadata_summary
    parts << metadata[:color] if metadata[:color]
    parts << metadata[:material] if metadata[:material]
    parts << metadata[:season] if metadata[:season]
    parts << metadata[:occasion] if metadata[:occasion]

    latest_analysis = inventory_item.ai_analyses.order(created_at: :desc).first
    if latest_analysis
      analysis_data = latest_analysis.analysis_data_hash
      parts << analysis_data["style"] if analysis_data["style"]
      parts << analysis_data["material"] if analysis_data["material"]
      parts.concat(analysis_data["colors"]) if analysis_data["colors"].is_a?(Array)
    end

    parts.compact.join(" ")
  end
end
