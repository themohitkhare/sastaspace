module Services
  class ShoesAnalyzer < InventoryAnalyzer
    def perform_analysis(chat)
      prompt = shoes_analysis_prompt
      
      user_message = chat.messages.create!(
        role: "user",
        content: prompt
      )
      
      assistant_message = chat.ask(role: "user", content: prompt)
      
      parse_analysis_response(assistant_message.content)
    end

    private

    def shoes_analysis_prompt
      <<~PROMPT
        You are a footwear analysis AI. Please analyze this shoe item and provide:
        
        1. Item type: #{inventory_item.item_type}
        2. Category: #{inventory_item.category&.name || "Not specified"}
        3. Brand: #{inventory_item.brand&.name || "Not specified"}
        4. Name: #{inventory_item.name}
        5. Colors: Extract dominant colors
        6. Style: Type of shoes (athletic, casual, formal, boots, sandals, etc.)
        7. Material: Upper and sole material
        8. Season: When to wear these
        9. Occasion: Appropriate occasions
        10. Size notes: Any sizing information visible
        11. Condition assessment: If visible
        12. Brand suggestion: If brand is not set
        13. Category suggestion: If category is wrong
        14. Confidence: Your confidence (0.0 to 1.0)
        
        Return valid JSON with these keys:
        {
          "item_type": "shoes",
          "colors": ["color1", "color2"],
          "style": "...",
          "material": "...",
          "season": "...",
          "occasion": "...",
          "size_notes": "...",
          "condition": "...",
          "brand_suggestion": "...",
          "category_suggestion": "...",
          "confidence": 0.85
        }
      PROMPT
    end

    def parse_analysis_response(content)
      json_match = content.match(/\{.*\}/m)
      
      if json_match
        JSON.parse(json_match[0])
      else
        {
          "item_type" => "shoes",
          "colors" => ["unknown"],
          "style" => "uncertain",
          "confidence" => 0.5
        }
      end
    rescue JSON::ParserError => e
      Rails.logger.error "Failed to parse analysis response: #{e.message}"
      {
        "item_type" => "shoes",
        "colors" => ["unknown"],
        "style" => "unable to analyze",
        "confidence" => 0.0
      }
    end

    def analysis_type
      "visual_analysis"
    end
  end
end

