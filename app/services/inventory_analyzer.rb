module Services
  # Base inventory analyzer using RubyLLM
  class InventoryAnalyzer
    attr_reader :inventory_item, :model_name

    def initialize(inventory_item, model_name: "gpt-4o-mini")
      @inventory_item = inventory_item
      @model_name = model_name
    end

    # Main analysis entry point
    def analyze
      chat = create_or_find_chat

      # Analyze the inventory item
      results = perform_analysis(chat)

      # Save results to AiAnalysis
      save_analysis(results)

      # Generate and store embedding
      generate_embedding

      results
    end

    private

    def create_or_find_chat
      # Find or create a chat for this analysis session
      Chat.find_or_create_by!(user: inventory_item.user, model_id: model.id) do |chat|
        Rails.logger.info "Creating new chat for analysis of inventory item #{inventory_item.id}"
      end
    end

    def model
      @model ||= Model.find_or_create_by!(
        provider: model_provider,
        model_id: model_name
      ) do |m|
        m.name = model_name
        m.context_window = 128_000
        m.family = "gpt-4"
      end
    end

    def model_provider
      "openai"
    end

    def perform_analysis(chat)
      # This will be implemented in subclasses
      raise NotImplementedError, "Subclasses must implement perform_analysis"
    end

    def analysis_prompt
      # Base prompt - subclasses can override
      "Analyze this #{inventory_item.item_type} and provide structured information."
    end

    def save_analysis(results)
      start_time = Time.current

      ai_analysis = AiAnalysis.create!(
        inventory_item: inventory_item,
        user: inventory_item.user,
        analysis_type: analysis_type,
        analysis_data: results,
        confidence_score: results["confidence"] || 0.8,
        model_used: model_name,
        processing_time_ms: calculate_processing_time(start_time),
        prompt_used: analysis_prompt,
        high_confidence: (results["confidence"] || 0) > 0.8
      )

      Rails.logger.info "Created AI analysis #{ai_analysis.id} for inventory item #{inventory_item.id}"
      ai_analysis
    end

    def generate_embedding
      # Use RubyLLM to generate embedding for the inventory item
      embedding = EmbeddingService.generate_for_item(inventory_item)

      inventory_item.update!(embedding_vector: embedding) if embedding.present?
    end

    def calculate_processing_time(start_time)
      ((Time.current - start_time) * 1000).to_i
    end

    def analysis_type
      "visual_analysis"
    end
  end
end
