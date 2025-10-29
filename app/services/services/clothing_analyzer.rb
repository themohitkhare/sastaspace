module Services
  class ClothingAnalyzer < InventoryAnalyzer
    def perform_analysis(chat)
      # Create a comprehensive prompt for clothing analysis
      prompt = clothing_analysis_prompt

      # Get the user's message with image context
      user_message = chat.messages.create!(
        role: "user",
        content: prompt
      )

      # Use RubyLLM to complete the chat
      assistant_message = chat.ask(role: "user", content: prompt)

      # Parse the response into structured data
      parse_analysis_response(assistant_message.content)
    end

    private

    def clothing_analysis_prompt
      <<~PROMPT
        You are a fashion analysis AI. Please analyze this clothing item and provide:

        1. Item type: #{inventory_item.item_type}
        2. Category: #{inventory_item.category&.name || "Not specified"}
        3. Brand: #{inventory_item.brand&.name || "Not specified"}
        4. Name: #{inventory_item.name}
        5. Colors: Extract dominant colors from the image
        6. Style: Describe the style (casual, formal, sporty, etc.)
        7. Material: Identify the material/fabric if visible
        8. Season: When should this be worn? (Spring, Summer, Fall, Winter, All-season)
        9. Occasion: Appropriate occasions (work, casual, formal, athletic, etc.)
        10. Fit notes: Note about fit or sizing
        11. Care instructions: Recommended care
        12. Brand suggestion: If brand is not set, suggest likely brands
        13. Category suggestion: If category is wrong, suggest correct category
        14. Confidence: Your confidence in this analysis (0.0 to 1.0)

        Return your response as valid JSON with these keys:
        {
          "item_type": "...",
          "colors": ["color1", "color2"],
          "style": "...",
          "material": "...",
          "season": "...",
          "occasion": "...",
          "fit_notes": "...",
          "care_instructions": "...",
          "brand_suggestion": "...",
          "category_suggestion": "...",
          "confidence": 0.85
        }
      PROMPT
    end

    def parse_analysis_response(content)
      # Try to extract JSON from the response
      json_match = content.match(/\{.*\}/m)

      if json_match
        JSON.parse(json_match[0])
      else
        # Fallback parsing
        {
          "item_type" => inventory_item.item_type,
          "colors" => extract_colors_from_text(content),
          "style" => "uncertain",
          "confidence" => 0.5
        }
      end
    rescue JSON::ParserError => e
      Rails.logger.error "Failed to parse analysis response: #{e.message}"
      {
        "item_type" => inventory_item.item_type,
        "colors" => [ "unknown" ],
        "style" => "unable to analyze",
        "confidence" => 0.0
      }
    end

    def extract_colors_from_text(text)
      color_words = [ "red", "blue", "green", "yellow", "black", "white", "gray", "grey",
                    "brown", "purple", "pink", "orange", "navy", "beige", "tan" ]
      found_colors = color_words.select { |color| text.downcase.include?(color) }
      found_colors.any? ? found_colors : [ "unknown" ]
    end

    def analysis_type
      "visual_analysis"
    end
  end
end
