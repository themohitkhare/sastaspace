module Services
  # Analyzer for extracting multiple inventory items from outfit photos
  # Uses qwen3-vl:8b vision model via Ollama to detect and analyze all items in an outfit
  class OutfitPhotoAnalyzer
    attr_reader :image_blob, :user, :model_name

    def initialize(image_blob:, user:, model_name: "qwen3-vl:8b")
      @image_blob = image_blob
      @user = user
      @model_name = model_name
    end

    # Main analysis entry point - returns array of detected items
    def analyze
      Rails.logger.info "Starting outfit photo analysis using #{model_name}"

      # Validate image blob
      unless image_blob.present?
        raise ArgumentError, "Image blob is required"
      end

      # Check Ollama availability
      check_ollama_availability!

      # Perform analysis with image
      results = perform_analysis

      # Check for parsing errors or low confidence
      if results["parse_error"] || (results["total_items"] || 0) == 0
        Rails.logger.warn "Analysis completed with parse error or no items detected: #{results.inspect}"
        # Don't fail, return partial results for graceful degradation
      end

      # Enhance results with category and brand matching for each item
      if results["items"].is_a?(Array)
        results["items"] = results["items"].map { |item| enhance_item_with_matching(item) }
      end

      results
    rescue ArgumentError => e
      Rails.logger.error "Invalid arguments for analysis: #{e.message}"
      {
        "error" => "Invalid request: #{e.message}",
        "items" => [],
        "total_items" => 0
      }
    rescue StandardError => e
      Rails.logger.error "Failed to analyze outfit photo: #{e.message}"
      Rails.logger.error e.backtrace.first(10).join("\n")
      {
        "error" => "Analysis failed: #{e.message}",
        "items" => [],
        "total_items" => 0
      }
    end

    private

    # Check Ollama availability - reuse same logic as InventoryCreationAnalyzer
    def check_ollama_availability!
      ollama_base = ENV["OLLAMA_API_BASE"] || "http://localhost:11434"
      base_uri = URI(ollama_base)

      Rails.logger.info "Checking Ollama availability at #{ollama_base}..."

      begin
        http = Net::HTTP.new(base_uri.host, base_uri.port)
        http.open_timeout = 3
        http.read_timeout = 3

        tags_response = http.get("/api/tags")
        unless tags_response.code == "200"
          raise StandardError, "Ollama API returned status #{tags_response.code}"
        end

        models_data = JSON.parse(tags_response.body)
        available_models = models_data["models"] || []

        model_exists = available_models.any? do |m|
          (m["name"] && (m["name"] == model_name || m["name"].start_with?("#{model_name}:"))) ||
          (m["model"] && (m["model"] == model_name || m["model"].start_with?("#{model_name}:")))
        end

        unless model_exists
          model_names = available_models.map { |m| m["name"] || m["model"] }.compact.join(", ")
          Rails.logger.warn "Model #{model_name} not found in Ollama. Available models: #{model_names}"
          raise StandardError, "Model #{model_name} is not available in Ollama. Available models: #{model_names}. Please pull it first: ollama pull #{model_name}"
        end

        Rails.logger.info "✓ Ollama is available and model #{model_name} is present"
      rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH, SocketError => e
        Rails.logger.error "Cannot connect to Ollama at #{ollama_base}: #{e.message}"
        raise StandardError, "Ollama service is not available at #{ollama_base}. Please ensure Ollama is running."
      rescue Net::ReadTimeout, Net::OpenTimeout, Timeout::Error => e
        Rails.logger.error "Timeout connecting to Ollama: #{e.message}"
        raise StandardError, "Timeout connecting to Ollama service. Please check if Ollama is running."
      rescue JSON::ParserError => e
        Rails.logger.error "Failed to parse Ollama response: #{e.message}"
        raise StandardError, "Ollama returned invalid response. Please check Ollama installation."
      rescue StandardError => e
        raise e if e.message.include?("Ollama") || e.message.include?("Model")
        Rails.logger.error "Error checking Ollama availability: #{e.message}"
        raise StandardError, "Failed to verify Ollama availability: #{e.message}"
      end
    end

    def perform_analysis
      prompt = analysis_prompt

      # Create a temporary chat for analysis
      chat = create_chat

      begin
        image_path = nil
        temp_file = nil

        # Try to get the file path from ActiveStorage (works for DiskService)
        if image_blob.service.respond_to?(:path_for)
          image_path = image_blob.service.path_for(image_blob.key)
        end

        # If we don't have a direct path, create a temp file
        unless image_path && File.exist?(image_path)
          require "tempfile"
          extension = image_blob.filename.extension_with_delimiter || ".jpg"
          temp_file = Tempfile.new([ "ollama_outfit", extension ])
          temp_file.binmode
          temp_file.write(image_blob.download)
          temp_file.flush
          image_path = temp_file.path
        end

        # Use RubyLLM's 'with:' parameter to pass the image file path
        assistant_message = chat.ask(prompt, with: image_path)

        # Clean up temp file if we created one
        if temp_file
          temp_file.close
          temp_file.unlink
        end

        unless assistant_message&.content.present?
          raise StandardError, "Empty response from AI model"
        end

        # Parse the response into structured data
        parse_analysis_response(assistant_message.content)
      rescue ArgumentError => e
        Rails.logger.error "Invalid arguments for chat.ask: #{e.message}"
        raise e
      rescue StandardError => e
        Rails.logger.error "Error during RubyLLM analysis: #{e.message}"
        if e.message.include?("connection") || e.message.include?("refused")
          raise StandardError, "Ollama service unavailable. Please ensure Ollama is running."
        end
        raise e
      end
    end

    def create_chat
      # Create a temporary chat for this analysis session
      model = Model.find_or_create_by!(
        provider: "ollama",
        model_id: model_name
      ) do |m|
        m.name = model_name
        m.context_window = 8192
        m.family = "gemma"
      end

      Chat.create!(
        user: user,
        model: model
      ).tap do |chat|
        Rails.logger.info "Created chat #{chat.id} for outfit photo analysis"
      end
    end

    def analysis_prompt
      # Get available categories to help the AI choose correctly
      available_categories = Category.active.order(:name).pluck(:name).join(", ")

      <<~PROMPT
        You are a fashion analysis AI. Analyze this image of a complete outfit and detect ALL individual clothing items, shoes, accessories, and jewelry visible in the photo.

        IMPORTANT: You MUST choose category_name for each item from the following list of available categories in the database:
        #{available_categories}

        If an item doesn't match any category exactly, choose the CLOSEST match from the list above.

        Detect and extract information for EACH separate item in the outfit. Return an array of items with the following structure:

        {
          "total_items": <number of items detected>,
          "items": [
            {
              "category_name": "Category name FROM THE LIST ABOVE - must match exactly or be very close",
              "name": "Descriptive name for this item (e.g., 'Blue Cotton T-Shirt', 'Nike Running Sneakers')",
              "description": "Rich, detailed description for vector search. Include: colors, materials, size if visible, style characteristics, fit details, seasonality, occasions suitable for, and any notable features. Be comprehensive and descriptive.",
              "brand_name": "Brand name if visible, or null if not visible",
              "style_notes": "Any additional style notes or observations about the item's aesthetic or design",
              "position": "Description of where this item appears in the outfit (e.g., 'top layer', 'bottom', 'footwear', 'accessory')",
              "confidence": 0.0 to 1.0
            },
            ... (repeat for each detected item)
          ]
        }

        Important:
        - Return ONLY valid JSON, no markdown formatting or additional text
        - Detect ALL visible items: clothing (tops, bottoms, outerwear), shoes, bags, accessories, jewelry, etc.
        - category_name MUST be from the available categories list above for each item
        - description should be RICH and COMPREHENSIVE for each item - include colors, materials, style, fit, season, occasion, and features
        - If information is not visible or unclear for an item, use null for that field (except description - always provide a description)
        - confidence should reflect how certain you are about each item's analysis
        - Include at least 2-3 items minimum (outfit typically has multiple pieces)
        - Be thorough but accurate - don't invent items that aren't clearly visible
      PROMPT
    end

    def parse_analysis_response(content)
      # Try to extract JSON from the response
      json_match = content.match(/\{[\s\S]*\}/m)

      if json_match
        parsed = JSON.parse(json_match[0])

        # Ensure items array exists
        parsed["items"] ||= []
        parsed["total_items"] = parsed["items"].length

        # Ensure each item has required fields
        parsed["items"] = parsed["items"].map do |item|
          item["confidence"] ||= 0.5
          item["description"] ||= "No description available"
          item["position"] ||= "unknown"
          item
        end

        parsed
      else
        Rails.logger.warn "Could not parse JSON from AI response: #{content.truncate(200)}"
        {
          "items" => [],
          "total_items" => 0,
          "parse_error" => true,
          "error" => "Could not parse response"
        }
      end
    rescue JSON::ParserError => e
      Rails.logger.error "JSON parse error: #{e.message}"
      {
        "items" => [],
        "total_items" => 0,
        "parse_error" => true,
        "error" => e.message
      }
    end

    def enhance_item_with_matching(item_data)
      # Match category from database
      if item_data["category_name"].present?
        matched_category = find_matching_category(item_data["category_name"])
        item_data["category_id"] = matched_category&.id
        item_data["category_matched"] = matched_category&.name
      end

      # Match brand from database
      if item_data["brand_name"].present?
        matched_brand = find_matching_brand(item_data["brand_name"])
        item_data["brand_id"] = matched_brand&.id
        item_data["brand_matched"] = matched_brand&.name
        item_data["brand_suggested"] = item_data["brand_name"] unless matched_brand
      end

      item_data
    end

    # Reuse category matching logic from InventoryCreationAnalyzer
    def find_matching_category(category_name)
      return nil if category_name.blank?

      normalized_name = category_name.downcase.strip

      # Exact match
      category = Category.active.where("LOWER(name) = ?", normalized_name).first
      return category if category

      # Synonym mapping (reuse from InventoryCreationAnalyzer)
      synonym_map = {
        "satchel" => "bags",
        "handbag" => "handbags",
        "backpack" => "backpacks",
        "tote" => "totes",
        "clutch" => "clutches",
        "purse" => "handbags",
        "messenger" => "bags",
        "boot" => "boots",
        "chelsea" => "ankle boots",
        "sneaker" => "sneakers",
        "runner" => "running shoes",
        "trainer" => "training shoes",
        "loafer" => "loafers",
        "sandals" => "sandals",
        "sandal" => "sandals",
        "slipper" => "slip-ons",
        "heels" => "heels",
        "heel" => "heels",
        "pump" => "pumps",
        "oxford" => "oxfords",
        "flat" => "dress flats",
        "t-shirt" => "t-shirts",
        "tshirt" => "t-shirts",
        "tee" => "t-shirts",
        "shirt" => "blouses",
        "jean" => "jeans",
        "pant" => "pants",
        "short" => "shorts",
        "skirt" => "skirts",
        "dress" => "dresses",
        "jacket" => "jackets",
        "coat" => "coats",
        "blazer" => "blazers",
        "cardigan" => "cardigans",
        "sweater" => "sweaters",
        "hoodie" => "hoodies",
        "hat" => "hats",
        "cap" => "baseball caps",
        "beanie" => "beanies",
        "sunglasses" => "sunglasses",
        "glasses" => "sunglasses",
        "necklace" => "necklaces",
        "ring" => "rings",
        "earring" => "earrings",
        "bracelet" => "bracelets",
        "watch" => "watches"
      }

      # Check synonyms
      input_words = normalized_name.split(/\s+/)
      input_words.each do |word|
        if synonym_map.key?(word)
          synonym_category = Category.active.where("LOWER(name) = ?", synonym_map[word]).first
          return synonym_category if synonym_category
        end
      end

      # Word-based matching
      significant_words = normalized_name.split(/\s+/).reject { |w| w.length < 3 }

      Category.active.find_each do |cat|
        cat_normalized = cat.name.downcase
        cat_words = cat_normalized.split(/\s+/)

        significant_words.each do |input_word|
          cat_words.each do |cat_word|
            if input_word == cat_word ||
               (input_word.length >= 4 && cat_word.start_with?(input_word[0..3])) ||
               (cat_word.length >= 4 && input_word.start_with?(cat_word[0..3]))
              return cat
            end
          end
        end

        if normalized_name.include?(cat_normalized) || cat_normalized.include?(normalized_name)
          return cat if normalized_name.length >= 3 && cat_normalized.length >= 3
        end
      end

      # Partial match
      partial_match = Category.active.where("LOWER(name) LIKE ?", "%#{normalized_name.split.first}%").first
      return partial_match if partial_match

      # Final fallback
      significant_words.each do |word|
        match = Category.active.where("LOWER(name) LIKE ?", "%#{word}%").first
        return match if match
      end

      nil
    end

    def find_matching_brand(brand_name)
      return nil if brand_name.blank?

      normalized_name = brand_name.downcase.strip

      # Exact match
      brand = Brand.where("LOWER(name) = ?", normalized_name).first
      return brand if brand

      # Fuzzy matching
      Brand.find_each do |b|
        brand_normalized = b.name.downcase
        if normalized_name.include?(brand_normalized) || brand_normalized.include?(normalized_name)
          return b if normalized_name.length >= 2 || brand_normalized.length >= 2
        end
      end

      # Partial match
      Brand.where("LOWER(name) LIKE ?", "%#{normalized_name}%").first
    end
  end
end
