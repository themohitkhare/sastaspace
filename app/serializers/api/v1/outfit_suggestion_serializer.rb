module Api
  module V1
    # Serializer for outfit suggestions with enhanced reasoning and match scores
    class OutfitSuggestionSerializer
      def initialize(suggestion_data)
        @item = suggestion_data[:item]
        @match_score = suggestion_data[:match_score] || 0.0
        @reasoning = suggestion_data[:reasoning] || {}
        @badges = suggestion_data[:badges] || []
      end

      def as_json
        # Use InventoryItemSerializer for base item data
        base_data = Api::V1::InventoryItemSerializer.new(@item).as_json

        # Add suggestion-specific fields
        base_data.merge(
          match_score: @match_score,
          reasoning: {
            primary: @reasoning[:primary] || "Style match",
            details: @reasoning[:details] || "Complements your outfit",
            tags: @reasoning[:tags] || []
          },
          badges: @badges
        )
      rescue StandardError => e
        Rails.logger.error "Error in OutfitSuggestionSerializer#as_json: #{e.message}"
        Rails.logger.error e.backtrace.first(10).join("\n")
        raise
      end
    end
  end
end
