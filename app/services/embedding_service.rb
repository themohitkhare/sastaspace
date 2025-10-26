module Services
  module EmbeddingService
    # Generate embedding for an inventory item
    def self.generate_for_item(inventory_item)
      return nil unless inventory_item.present?
      
      description = build_item_description(inventory_item)
      generate_text_embedding(description)
    end

    # Generate embedding from text directly
    def self.generate_text_embedding(text)
      return nil if text.blank?
      
      # TODO: Replace with actual RubyLLM embedding generation
      # For now, return a placeholder vector
      # This will be replaced with: RubyLLM.embed(text, model: "text-embedding-3-small")
      
      # Placeholder 1536-dimensional vector (OpenAI ada-002 dimensions)
      Rails.logger.warn "Using placeholder embedding"
      Array.new(1536) { rand(-1.0..1.0) }
    end

    private

    def self.build_item_description(inventory_item)
      parts = []
      
      # Basic info
      parts << inventory_item.name
      parts << inventory_item.item_type
      parts << inventory_item.category.name if inventory_item.category
      parts << inventory_item.brand.name if inventory_item.brand
      
      # Metadata
      metadata = inventory_item.metadata_summary
      parts << metadata[:color] if metadata[:color]
      parts << metadata[:material] if metadata[:material]
      parts << metadata[:season] if metadata[:season]
      parts << metadata[:occasion] if metadata[:occasion]
      
      # Get latest analysis data if available
      latest_analysis = inventory_item.ai_analyses.order(created_at: :desc).first
      if latest_analysis
        analysis_data = latest_analysis.analysis_data_hash
        parts << analysis_data["style"] if analysis_data["style"]
        parts << analysis_data["material"] if analysis_data["material"]
        if analysis_data["colors"].is_a?(Array)
          parts.concat(analysis_data["colors"])
        end
      end
      
      parts.compact.join(" ")
    end
  end
end
