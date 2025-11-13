module Services
  # Builds specialized extraction prompts for ComfyUI stock photo generation
  # Integrates with RubyLLM analysis results and user gender preferences
  class ExtractionPromptBuilder
    attr_reader :item_data, :user

    def initialize(item_data:, user:)
      @item_data = item_data
      @user = user
    end

    def build_prompt
      <<~PROMPT
        PROFESSIONAL STOCK PHOTO EXTRACTION - #{item_name.upcase}

        Gender Context: #{gender_context}
        Category: #{category_info}

        Item Specifications:
        #{color_specifications}
        #{material_specifications}
        #{pattern_specifications}
        #{brand_specifications}

        Extraction Requirements:
        1. REMOVE all background elements → Pure white (#FFFFFF)
        2. REMOVE person/model → Garment only
        3. PRESERVE exact colors and color relationships
        4. PRESERVE all fabric texture, material detail, and construction
        5. PRESERVE brand elements (logos, tags, details)
        6. MAINTAIN natural garment shape and drape
        7. SHOW all functional details (zippers, buttons, pockets, drawstrings)

        Technical Output:
        - Background: Pure white, no gradients or shadows
        - Resolution: Minimum 800x800 pixels
        - Placement: Centered, front-facing
        - Lighting: Even, professional e-commerce style
        - Quality: High-resolution, sharp details
        - Format: Clean PNG with transparency where appropriate

        DO NOT:
        - Add artificial shadows or backgrounds
        - Alter colors from original
        - Remove functional garment details
        - Distort proportions or fit
        - Add watermarks or overlays
      PROMPT
    end

    private

    def item_name
      item_data["name"] || item_data["category_name"] || "Clothing Item"
    end

    def gender_context
      user.gender_preference&.capitalize || "Unisex"
    end

    def category_info
      category = item_data["category_matched"] || item_data["category_name"]
      subcategory = item_data["subcategory"]
      result = category.to_s
      result += " > #{subcategory}" if subcategory.present?
      result
    end

    def color_specifications
      colors = item_data["colors"] || []
      return "" if colors.empty?

      primary = colors.first
      secondary = colors[1..-1].join(", ")

      specs = "- Primary Color: #{primary} - maintain exact shade"
      specs += "\n- Secondary Colors: #{secondary}" if secondary.present?
      specs
    end

    def material_specifications
      material = item_data["material"]
      return "" unless material.present?

      "- Material: #{material} - show fabric texture clearly"
    end

    def pattern_specifications
      style = item_data["style"] || item_data["style_notes"]
      return "" unless style.present?

      "- Style/Pattern: #{style}"
    end

    def brand_specifications
      brand = item_data["brand_matched"] || item_data["brand_name"] || item_data["brand_suggestion"]
      return "" unless brand.present?

      "- Brand: #{brand} - keep logo visible if present"
    end
  end
end
