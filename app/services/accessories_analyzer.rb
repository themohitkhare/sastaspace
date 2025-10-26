module Services
  class AccessoriesAnalyzer < InventoryAnalyzer
    def perform_analysis(chat)
      prompt = accessories_analysis_prompt
      
      user_message = chat.messages.create!(
        role: "user",
        content: prompt
      )
      
      assistant_message = chat.ask(role: "user", content: prompt)
      
      parse_analysis_response(assistant_message.content)
    end

    private

    def accessories_analysis_prompt
      <<~PROMPT
        You are an accessories analysis AI. Please analyze this accessory item and provide:
        
        1. Item type: #{inventory_item.item_type}
        2. Category: #{inventory_item.category&.name || "Not specified"}
        3. Brand: #{inventory_item.brand&.name || "Not specified"}
        4. Name: #{inventory_item.name}
        5. Colors: Extract dominant colors
        6. Type: Specific type (bag, belt, hat, scarf, etc.)
        7. Style: Describe the style
        8. Material: Identify the material
        9. Season: When to wear
        10. Occasion: Appropriate occasions
        11. Size/Size notes: Any sizing info
        12. Brand suggestion: If brand is not set
        13. Category suggestion: If category is wrong
        14. Confidence: Your confidence (0.0 to 1.0)
        
        Return valid JSON with these keys:
        {
          "item_type": "accessories",
          "colors": ["color1", "color2"],
          "accessory_type": "...",
          "style": "...",
          "material": "...",
          "season": "...",
          "occasion": "...",
          "size_notes": "...",
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
          "item_type" => "accessories",
          "colors" => ["unknown"],
          "style" => "uncertain",
          "confidence" => 0.5
        }
      end
    rescue JSON::ParserError => e
      Rails.logger.error "Failed to parse analysis response: #{e.message}"
      {
        "item_type" => "accessories",
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

