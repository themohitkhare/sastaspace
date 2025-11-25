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
        *** PROFESSIONAL E-COMMERCE PRODUCT PHOTOGRAPHY GENERATION ***
        Target Subject: #{item_name.upcase}

        CRITICAL SOURCE IMAGE FILTERING:
        - IF source is a screenshot with UI elements (buttons, menus, app interface, borders), EXTRACT ONLY the clothing item itself
        - IGNORE all digital overlays, phone frames, app interfaces, navigation elements, text overlays, watermarks
        - IF clothing appears within a photo inside a screenshot (social media post, shopping app), extract ONLY that specific clothing item
        - Focus EXCLUSIVELY on the physical clothing/accessory product itself, not the digital container it's displayed in

        CONTEXT:
        Transform the source image into a premium e-commerce product photograph suitable for high-end fashion retail websites like Zara, H&M, Uniqlo, or luxury brands.
        Create a professional product photo that customers would see on an online shopping website.

        ITEM DETAILS:
        Category: #{category_info}
        Gender: #{gender_context}
        Description: #{description_section}

        VISUAL SPECIFICATIONS:
        #{color_specifications}
        #{material_specifications}
        #{pattern_specifications}
        #{brand_specifications}

        PRESENTATION STYLE (Category-Specific):
        #{presentation_style_for_category}

        GENERATION DIRECTIVES:
        1. SOURCE FILTERING: If source is a screenshot or contains UI elements, extract ONLY the #{item_name} itself. Completely remove: screenshot borders, UI buttons, app interfaces, navigation bars, status bars, phone frames, social media overlays, watermarks, text overlays, digital artifacts.
        2. SUBJECT FOCUS: Completely isolate the #{item_name}. Remove ALL human elements: person, model, body parts, hands, arms, legs, face, hair, skin.
        3. PRESENTATION: #{presentation_instruction}
        4. COMPOSITION: Centered, professional product photography composition. Item should fill 75-85% of frame. Maintain natural proportions.
        5. LIGHTING: Professional e-commerce studio lighting - soft, even, diffused. No harsh shadows. Neutral white balance (5500K). Subtle rim lighting to show texture and depth.
        6. BACKGROUND: Pure solid white background (#FFFFFF, RGB 255,255,255). Completely seamless, no gradients, no shadows, no texture. Professional product photography standard.
        7. FIDELITY: PRESERVE exact colors, textures, patterns, logos, and material details from the CLOTHING ITEM ONLY. Do NOT invent new features, colors, or details.
        8. RESTORATION: If parts were obscured (by body, arms, hair, UI elements, or other objects), intelligently reconstruct them to show the complete garment naturally and accurately.
        9. QUALITY: High-resolution, sharp focus throughout. Professional product photography quality suitable for zoom-in detail views.
        10. ORIENTATION: Front-facing view showing the item as it would appear on a product page. For tops/jackets: show front with collar/opening visible. For bottoms: show front with waistband and leg opening visible.

        SPECIFIC REQUIREMENTS:
        #{description_based_requirements}
        #{category_specific_requirements}

        NEGATIVE PROMPT (STRICTLY AVOID):
        human, person, model, body parts, skin, hands, arms, legs, face, hair, mannequin stand, visible mannequin, plastic mannequin, tied around waist, draped, worn, styled, messy background, noise, blur, distortion, low resolution, watermarks, text, overlay, filters, strong vignette, high contrast, dark shadows, colored background, gradient background, texture background, shadows on background, product tags visible, price tags, hangers visible, wrinkles, creases, folds that obscure details, casual styling, street style, lifestyle photography, screenshot UI, app interface, buttons, navigation bars, phone frame, digital borders, status bar, social media interface, website chrome, browser elements, menu overlays, popup windows, notification badges, UI elements.
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

    def description_section
      description = item_data["description"]
      return "No description provided." unless description.present?

      # Clean and format the description
      cleaned = description.strip
      # If description is long, keep it but ensure it's readable
      cleaned
    end

    def presentation_style_for_category
      category = category_info.downcase

      if category.include?("sweater") || category.include?("hoodie") || category.include?("cardigan") || category.include?("pullover")
        "For sweaters/knitwear: Present as a clean, flat lay on white background OR on invisible/ghost mannequin showing natural drape. Show full garment shape, sleeves extended naturally, front and back visible. DO NOT show it tied, draped, or casually styled."
      elsif category.include?("jacket") || category.include?("coat") || category.include?("blazer")
        "For outerwear: Present on invisible/ghost mannequin style showing 3D shape and fit. Front view with collar/lapels clearly visible. Zippers/buttons should be visible and properly aligned. Show natural drape and structure."
      elsif category.include?("shirt") || category.include?("blouse") || category.include?("top") || category.include?("t-shirt")
        "For tops/shirts: Present on invisible/ghost mannequin OR flat lay. If ghost mannequin, show natural fit. If flat lay, show front fully spread with collar, buttons, and sleeves visible. Professional product photography style."
      elsif category.include?("pant") || category.include?("trouser") || category.include?("jean") || category.include?("bottom")
        "For bottoms: Present on invisible/ghost mannequin showing natural fit and drape. Front view with waistband, fly, and leg opening clearly visible. Show proper length and fit."
      elsif category.include?("dress")
        "For dresses: Present on invisible/ghost mannequin showing full silhouette. Front view with neckline, waist, and hem clearly visible. Show natural drape and fit."
      elsif category.include?("shoe") || category.include?("boot") || category.include?("sneaker")
        "For footwear: Present as professional product photography - side view and front view. Show sole, laces, and all details clearly. Clean, centered composition."
      elsif category.include?("accessor") || category.include?("bag") || category.include?("belt")
        "For accessories: Present as clean flat lay or product photography. Show all details, hardware, and features clearly. Professional e-commerce style."
      else
        "Present in professional e-commerce product photography style: either invisible/ghost mannequin for garments showing fit, or clean flat lay for items. Show item in its natural, unworn state suitable for online retail."
      end
    end

    def presentation_instruction
      category = category_info.downcase

      if category.include?("sweater") || category.include?("hoodie") || category.include?("cardigan")
        "Present as a clean, professional flat lay OR on invisible mannequin. Show the complete garment in its natural, unworn state. DO NOT show it tied around waist, draped, or casually styled. It should look like a new product ready for sale."
      elsif category.include?("jacket") || category.include?("coat") || category.include?("blazer")
        "Present on invisible/ghost mannequin showing 3D shape. Front view with all details visible. Professional fashion retail photography style."
      elsif category.include?("shirt") || category.include?("blouse") || category.include?("top")
        "Present on invisible mannequin OR as professional flat lay. Show complete garment front with all details visible. E-commerce product page style."
      elsif category.include?("pant") || category.include?("trouser") || category.include?("jean")
        "Present on invisible mannequin showing natural fit. Front view with waistband and leg details visible. Professional retail photography."
      else
        "Present in professional e-commerce product photography style: invisible/ghost mannequin for garments showing fit, or clean flat lay. Show item in its natural, unworn, ready-for-sale state."
      end
    end

    def category_specific_requirements
      category = category_info.downcase
      requirements = []

      if category.include?("sweater") || category.include?("hoodie") || category.include?("cardigan")
        requirements << "- Show complete sweater shape: front, back, sleeves, collar/neckline"
        requirements << "- Display knit texture and pattern clearly"
        requirements << "- Show ribbed cuffs and hem if present"
        requirements << "- DO NOT show it tied, wrapped, or casually draped"
        requirements << "- Present as a new, unworn product ready for sale"
      elsif category.include?("jacket") || category.include?("coat")
        requirements << "- Show front closure (zipper/buttons) clearly"
        requirements << "- Display collar/lapels properly"
        requirements << "- Show pockets and all functional details"
        requirements << "- Maintain structured silhouette"
      elsif category.include?("shirt") || category.include?("blouse")
        requirements << "- Show collar style and placket clearly"
        requirements << "- Display all buttons and buttonholes"
        requirements << "- Show sleeve cuffs and length"
        requirements << "- Present front view with all details visible"
      end

      requirements.join("\n        ")
    end

    def description_based_requirements
      description = item_data["description"]
      return "" unless description.present?

      # Extract key details from description that might inform extraction
      requirements = []

      # Check for specific features mentioned in description
      desc_lower = description.downcase

      # Remove confusing styling references
      if desc_lower.include?("draped") || desc_lower.include?("tied") || desc_lower.include?("wrapped")
        requirements << "IMPORTANT: Remove any styling where item is draped, tied, or wrapped. Show item in its natural, unworn state."
      end

      if desc_lower.include?("pocket") || desc_lower.include?("pockets")
        requirements << "ENSURE all pockets are clearly visible and properly positioned"
      end

      if desc_lower.include?("zipper") || desc_lower.include?("zippers")
        requirements << "SHOW zipper details clearly, including pull tab and teeth"
      end

      if desc_lower.include?("button") || desc_lower.include?("buttons")
        requirements << "DISPLAY all buttons clearly, showing their style and placement"
      end

      if desc_lower.include?("hood") || desc_lower.include?("hoodie")
        requirements << "SHOW hood details if applicable, including drawstrings"
      end

      if desc_lower.include?("collar") || desc_lower.include?("neckline")
        requirements << "PRESERVE collar/neckline style and structure"
      end

      if desc_lower.include?("sleeve") || desc_lower.include?("sleeves")
        requirements << "MAINTAIN sleeve length and style as described"
      end

      if desc_lower.include?("fit") || desc_lower.include?("cut")
        requirements << "PRESERVE the described fit and cut characteristics"
      end

      if desc_lower.include?("ribbed") || desc_lower.include?("ribbing")
        requirements << "SHOW ribbed texture clearly (cuffs, hem, waistband)"
      end

      if desc_lower.include?("knit") || desc_lower.include?("knitting")
        requirements << "DISPLAY knit pattern and texture clearly"
      end

      requirements.join("\n        ")
    end
  end
end
