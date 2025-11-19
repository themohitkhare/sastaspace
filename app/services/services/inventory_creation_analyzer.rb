module Services
  # Analyzer for extracting inventory item data from images during creation
  # Uses qwen3-vl:8b vision model via Ollama
  class InventoryCreationAnalyzer
    attr_reader :image_blob, :user, :model_name

    def initialize(image_blob:, user:, model_name: "qwen3-vl:8b")
      @image_blob = image_blob
      @user = user
      @model_name = model_name
    end

    # Main analysis entry point - returns structured inventory data
    def analyze
      Rails.logger.info "Starting image analysis for inventory creation using #{model_name}"

      # Validate image blob
      unless image_blob.present?
        raise ArgumentError, "Image blob is required"
      end

      # Check Ollama availability and model presence using HTTP (like curl)
      check_ollama_availability!

      # Perform analysis with image (using RubyLLM.chat directly, no Chat model needed)
      results = perform_analysis

      # Check for parsing errors or low confidence
      if results["parse_error"] || (results["confidence"] || 0) < 0.1
        Rails.logger.warn "Analysis completed with low confidence or parse error: #{results.inspect}"
        # Don't fail, return partial results for graceful degradation
      end

      # Enhance results with category and brand matching
      enhance_with_matching(results)

      # Generate extraction prompt for ComfyUI stock photo extraction
      generate_extraction_prompt(results)

      results
    rescue ArgumentError => e
      Rails.logger.error "Invalid arguments for analysis: #{e.message}"
      {
        "error" => "Invalid request: #{e.message}",
        "confidence" => 0.0
      }
    rescue StandardError => e
      Rails.logger.error "Failed to analyze image for inventory creation: #{e.message}"
      Rails.logger.error e.backtrace.first(10).join("\n")
      {
        "error" => "Analysis failed: #{e.message}",
        "confidence" => 0.0
      }
    end

    private

    # Check Ollama availability and model presence using HTTP requests (similar to curl)
    def check_ollama_availability!
      ollama_base = ENV["OLLAMA_API_BASE"] || "http://localhost:11434"
      base_uri = URI(ollama_base)

      Rails.logger.info "Checking Ollama availability at #{ollama_base}..."

      # Check if Ollama service is reachable (like: curl http://localhost:11434/api/tags)
      begin
        http = Net::HTTP.new(base_uri.host, base_uri.port)
        http.open_timeout = 10  # Increased from 3s - allow time for Ollama to start
        http.read_timeout = 120  # Increased from 3s - AI vision models need time to process

        # Check if Ollama is up
        tags_response = http.get("/api/tags")
        unless tags_response.code == "200"
          raise StandardError, "Ollama API returned status #{tags_response.code}"
        end

        # Parse response and check if model exists
        models_data = JSON.parse(tags_response.body)
        available_models = models_data["models"] || []

        # Check if our model is in the list
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
        raise StandardError, "Ollama service is not available at #{ollama_base}. Please ensure Ollama is running. You can test with: curl #{ollama_base}/api/tags"
      rescue Net::ReadTimeout, Net::OpenTimeout, Timeout::Error => e
        Rails.logger.error "Timeout connecting to Ollama: #{e.message}"
        raise StandardError, "Timeout connecting to Ollama service. Please check if Ollama is running."
      rescue JSON::ParserError => e
        Rails.logger.error "Failed to parse Ollama response: #{e.message}"
        raise StandardError, "Ollama returned invalid response. Please check Ollama installation."
      rescue StandardError => e
        # Re-raise if it's our custom error, otherwise wrap it
        raise e if e.message.include?("Ollama") || e.message.include?("Model")
        Rails.logger.error "Error checking Ollama availability: #{e.message}"
        raise StandardError, "Failed to verify Ollama availability: #{e.message}"
      end
    end

    def perform_analysis
      prompt = analysis_prompt
      image_data = prepare_image_data

      unless image_data.present?
        raise ArgumentError, "Could not prepare image data"
      end

      # Create a temporary chat for analysis
      chat = create_chat

      # For Ollama vision models, we need to pass the image to chat.ask
      # RubyLLM supports passing images using the 'with:' parameter which accepts a file path
      # We need to get a file path from the ActiveStorage blob
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
          temp_file = Tempfile.new([ "ollama_image", extension ])
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
        # Log and re-raise argument errors
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
      # We need a model record for the chat
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
        Rails.logger.info "Created chat #{chat.id} for image analysis"
      end
    end

    def prepare_image_data
      # Convert ActiveStorage blob to base64 data URI for vision API
      return nil unless image_blob.present?

      # Download blob data
      image_data = image_blob.download

      # Convert to base64
      base64_data = Base64.strict_encode64(image_data)

      # Get content type
      content_type = image_blob.content_type || "image/jpeg"

      # Return data URI format
      "data:#{content_type};base64,#{base64_data}"
    end

    def analysis_prompt
      # Get available categories to help the AI choose correctly
      available_categories = Category.active.order(:name).pluck(:name).join(", ")
      gender_context = user.gender_preference || "unisex"

      <<~PROMPT
        You are a fashion analysis AI. Analyze this image of a clothing/fashion item and extract all relevant information for creating an inventory item.

        USER GENDER PREFERENCE: #{gender_context.upcase}
        IMPORTANT: This item should be appropriate for #{gender_context} fashion. If the item is clearly for a different gender, note this in your confidence score and set gender_appropriate to false.

        IMPORTANT: You MUST choose a category_name from the following list of available categories in the database:
        #{available_categories}

        If the item doesn't match any category exactly, choose the CLOSEST match. For example:
        - "Satchel", "Handbag", "Tote", "Backpack", "Purse" → use "Bags" (if available) or the closest match
        - "Chelsea Boots", "Ankle Boots" → use "Boots" or "Ankle Boots" (if available)
        - Use the most specific category that exists in the list above

        Extract and return the following information as valid JSON:

        {
          "category_name": "Category name FROM THE LIST ABOVE - must match exactly or be very close (this is critical for matching)",
          "name": "Descriptive name for this item (e.g., 'Blue Cotton T-Shirt', 'Nike Running Sneakers')",
          "description": "Rich, detailed description for vector search. Include: colors, materials, size if visible, style characteristics, fit details, seasonality, occasions suitable for, and any notable features. Be comprehensive and descriptive - this will be used for semantic search. Example: 'A vibrant mint green structured leather satchel with a clean, minimalist aesthetic. Features include a top handle, detachable shoulder strap, secure closure, and visible stitching. The structured design maintains its shape and provides a polished, professional look. Suitable for everyday use, work, and casual occasions. Made from high-quality leather with silver hardware accents. This versatile bag transitions well across seasons.'",
          "brand_name": "Brand name if visible, or null if not visible",
          "colors": ["primary_color", "secondary_color", ...],
          "style": "Style descriptor (e.g., 'athletic streetwear', 'business casual')",
          "material": "Material/fabric type (e.g., 'cotton blend fleece')",
          "season": "Appropriate season (Spring/Summer/Fall/Winter/All-season)",
          "occasion": "Suitable occasions (casual/athletic/formal/business/etc.)",
          "fit_notes": "Fit characteristics (e.g., 'relaxed fit', 'slim cut')",
          "care_instructions": "Care recommendations (e.g., 'machine wash cold')",
          "brand_suggestion": "Suggested brand if not visible",
          "category_suggestion": "Suggested category if yours seems wrong",
          "style_notes": "Any additional style notes or observations about the item's aesthetic or design",
          "gender_appropriate": true/false (is this item appropriate for user's gender preference?),
          "confidence": 0.0 to 1.0
        }

        Important:
        - Return ONLY valid JSON, no markdown formatting or additional text
        - category_name MUST be from the available categories list above - this is critical for successful matching
        - description should be RICH and COMPREHENSIVE - include colors, materials, style, fit, season, occasion, and features. This is used for vector search.
        - gender_appropriate should be true if the item matches the user's gender preference, false otherwise
        - If information is not visible or unclear, use null for that field (except description - always provide a description)
        - confidence should reflect how certain you are about the overall analysis
      PROMPT
    end

    def parse_analysis_response(content)
      # Try to extract JSON from the response
      json_match = content.match(/\{[\s\S]*\}/m)

      if json_match
        parsed = JSON.parse(json_match[0])
        # Ensure required fields exist
        parsed["confidence"] ||= 0.5
        parsed["description"] ||= "No description available"
        # Default gender_appropriate to true if not present (backwards compatibility)
        parsed["gender_appropriate"] = true if parsed["gender_appropriate"].nil?
        parsed
      else
        Rails.logger.warn "Could not parse JSON from AI response: #{content.truncate(200)}"
        {
          "category_name" => nil,
          "name" => "Unidentified Item",
          "description" => content.truncate(500),
          "brand_name" => nil,
          "style_notes" => nil,
          "gender_appropriate" => true,
          "confidence" => 0.2,
          "parse_error" => true
        }
      end
    rescue JSON::ParserError => e
      Rails.logger.error "JSON parse error: #{e.message}"
      {
        "category_name" => nil,
        "name" => "Unidentified Item",
        "description" => "Could not parse analysis results",
        "brand_name" => nil,
        "style_notes" => nil,
        "gender_appropriate" => true,
        "confidence" => 0.0,
        "parse_error" => true,
        "error" => e.message
      }
    end

    def enhance_with_matching(results)
      # Match category from database
      if results["category_name"].present?
        matched_category = find_matching_category(results["category_name"])
        results["category_id"] = matched_category&.id
        results["category_matched"] = matched_category&.name
      end

      # Match brand from database
      if results["brand_name"].present?
        matched_brand = find_matching_brand(results["brand_name"])
        results["brand_id"] = matched_brand&.id
        results["brand_matched"] = matched_brand&.name
        results["brand_suggested"] = results["brand_name"] unless matched_brand
      end

      results
    end

    def find_matching_category(category_name)
      return nil if category_name.blank?

      # Normalize the input
      normalized_name = category_name.downcase.strip

      # First, try exact match (case-insensitive)
      category = Category.active.where("LOWER(name) = ?", normalized_name).first
      return category if category

      # Map common synonyms to category names
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

      # Check synonyms first
      input_words = normalized_name.split(/\s+/)
      input_words.each do |word|
        if synonym_map.key?(word)
          synonym_category = Category.active.where("LOWER(name) = ?", synonym_map[word]).first
          return synonym_category if synonym_category
        end
      end

      # Try word-based matching for compound names (e.g., "Structured Leather Satchel" -> "Bags")
      # Split input into words and try to match each word
      significant_words = normalized_name.split(/\s+/).reject { |w| w.length < 3 }

      Category.active.find_each do |cat|
        cat_normalized = cat.name.downcase
        cat_words = cat_normalized.split(/\s+/)

        # Check if any significant word matches
        significant_words.each do |input_word|
          cat_words.each do |cat_word|
            # Match whole words (for better precision)
            if input_word == cat_word ||
               (input_word.length >= 4 && cat_word.start_with?(input_word[0..3])) ||
               (cat_word.length >= 4 && input_word.start_with?(cat_word[0..3]))
              return cat
            end
          end
        end

        # Also check if category name is contained in input or vice versa
        if normalized_name.include?(cat_normalized) || cat_normalized.include?(normalized_name)
          return cat if normalized_name.length >= 3 && cat_normalized.length >= 3
        end
      end

      # Try partial match as last resort (less precise but might catch something)
      partial_match = Category.active.where("LOWER(name) LIKE ?", "%#{normalized_name.split.first}%").first
      return partial_match if partial_match

      # Final fallback: try any word from input
      significant_words.each do |word|
        match = Category.active.where("LOWER(name) LIKE ?", "%#{word}%").first
        return match if match
      end

      nil
    end

    def find_matching_brand(brand_name)
      return nil if brand_name.blank?

      # Normalize the input
      normalized_name = brand_name.downcase.strip

      # Try exact match (case-insensitive)
      brand = Brand.where("LOWER(name) = ?", normalized_name).first
      return brand if brand

      # Try fuzzy matching
      Brand.find_each do |b|
        brand_normalized = b.name.downcase
        if normalized_name.include?(brand_normalized) || brand_normalized.include?(normalized_name)
          return b if normalized_name.length >= 2 || brand_normalized.length >= 2
        end
      end

      # Try partial match
      Brand.where("LOWER(name) LIKE ?", "%#{normalized_name}%").first
    end

    def generate_extraction_prompt(results)
      # Only generate prompt if we have valid analysis results
      return if results["error"].present? || results["parse_error"]

      begin
        prompt_builder = Services::ExtractionPromptBuilder.new(
          item_data: results,
          user: user
        )

        results["extraction_prompt"] = prompt_builder.build_prompt
        Rails.logger.info "Generated extraction prompt for inventory creation analysis"
      rescue StandardError => e
        Rails.logger.warn "Failed to generate extraction prompt: #{e.message}"
        # Don't fail the entire analysis if prompt generation fails
        results["extraction_prompt"] = nil
      end
    end
  end
end
