# Service for detecting multiple clothing items in a single image
# Uses RubyLLM with Qwen3-VL model via Ollama
class ClothingDetectionService
  attr_reader :image_blob, :user, :model_name

  DETECTION_PROMPT = <<~PROMPT
    CLOTHING DETECTION FOR SASTASPACE INVENTORY

    Analyze this image and identify ALL UNIQUE clothing and fashion items visible on all people. Return only valid JSON.

    CRITICAL RULES FOR UNIQUE ITEM IDENTIFICATION:
    - Each physical item should be identified EXACTLY ONCE - no duplicates
    - If you see a yellow floral shirt, list it as ONE item (not as both "dress" and "shirt")
    - Choose the MOST ACCURATE category for each item - don't list the same item under multiple categories
    - Example: A yellow floral garment is either a "shirt" OR a "dress", not both
    - If uncertain about category, choose the most specific one that fits
    - Count distinct physical items, not possible interpretations

    CRITICAL IMAGE FILTERING RULES:
    - IF this is a screenshot containing UI elements (buttons, menus, app interface, text overlays, watermarks, borders), IGNORE all non-clothing content
    - IF image contains phone frames, app interfaces, or digital overlays, focus ONLY on the actual clothing visible through/in the image
    - IF clothing is shown in a photo within a screenshot (e.g., social media post, shopping app), analyze ONLY the clothing in that inner photo
    - IGNORE: UI buttons, navigation bars, text overlays, app interfaces, watermarks, logos that aren't part of the clothing item itself
    - Focus EXCLUSIVELY on physical clothing and accessories worn by people in the photo

    {
      "total_items_detected": number,
      "people_count": number,
      "items": [
        {
          "id": "item_001",
          "item_name": "specific name",
          "category": "tops/bottoms/outerwear/shoes/accessories",
          "subcategory": "shirt/jeans/jacket/sneakers",
          "description": "Rich, detailed description for vector search. Include: colors, materials, size if visible, style characteristics, fit details, seasonality, occasions suitable for, and any notable features. Be comprehensive and descriptive. Example: 'A vibrant mint green structured leather satchel with a clean, minimalist aesthetic. Features include a top handle, detachable shoulder strap, secure closure, and visible stitching. The structured design maintains its shape and provides a polished, professional look. Suitable for everyday use, work, and casual occasions.'",
          "color_primary": "dominant color",
          "color_secondary": "secondary color if visible",
          "pattern_type": "solid/striped/geometric",
          "pattern_details": "vertical stripes, cable knit",
          "material_type": "cotton/knit/denim",
          "style_category": "casual/formal/sporty",
          "gender_styling": "men/women/unisex",
          "extraction_priority": "high/medium/low",
          "confidence": 0.0-1.0
        }
      ]
    }

    GENDER STYLING GUIDELINES:
    - "men": Items cut/styled for masculine presentation (men's shirts, suits, men's jeans, ties, etc.)
    - "women": Items cut/styled for feminine presentation (dresses, skirts, women's blouses, heels, etc.)
    - "unisex": Gender-neutral styling (basic t-shirts, hoodies, sneakers, accessories)

    Focus on the CLOTHING STYLE, not the person wearing it.

    IMPORTANT:
    - Return ONLY valid JSON, no markdown formatting or additional text
    - Detect ALL UNIQUE visible items: clothing (tops, bottoms, outerwear), shoes, bags, accessories, jewelry, etc.
    - Each physical item should appear EXACTLY ONCE in the list - NO DUPLICATES
    - If unsure between categories (e.g., is it a dress or a long shirt?), choose the MOST ACCURATE one and list it ONCE
    - description should be RICH and COMPREHENSIVE for each item - include colors, materials, style, fit, season, occasion, and features. This is used for vector search and inventory management.
    - gender_styling MUST be one of: "men", "women", or "unisex" for each item
    - extraction_priority should reflect how important/visible each item is
    - confidence should reflect how certain you are about each item's analysis
    - Be thorough but accurate - don't invent items that aren't clearly visible
    - DUPLICATE CHECK: Before finalizing, review your list and remove any duplicate items (same physical garment listed twice)
    - SCREENSHOT FILTERING: If this is a screenshot with UI elements, analyze ONLY the clothing items visible in the actual photo, NOT the UI elements, buttons, or interface

    EXAMPLES OF CORRECT DETECTION:
    ✓ CORRECT: One yellow floral shirt detected as {"item_name": "Yellow Floral Button-Up Shirt", "category": "tops", "subcategory": "shirt"}
    ✗ WRONG: Same item detected twice as "Light-Colored Patterned Dress" AND "Yellow Polo Shirt"

    ✓ CORRECT: Black trousers detected once as {"item_name": "Black Dress Trousers", "category": "bottoms"}
    ✗ WRONG: Same trousers detected as "Dark Trousers" AND "Black Pants"
  PROMPT

  def initialize(image_blob:, user:, model_name: "qwen3-vl:8b")
    @image_blob = image_blob
    @user = user
    @model_name = model_name
  end

  # Main analysis entry point - returns structured detection data
  def analyze
    Rails.logger.info "Starting clothing detection analysis using #{model_name}"

    # Validate inputs
    unless image_blob.present?
      raise ArgumentError, "Image blob is required"
    end

    unless user.present?
      raise ArgumentError, "User is required"
    end

    # Check Ollama availability (reuse pattern from OutfitPhotoAnalyzer)
    check_ollama_availability!

    # Perform analysis
    results = perform_analysis

    # Validate and enhance results
    results = validate_and_enhance_results(results)

    # Enhance items with category and brand matching
    if results["items"].is_a?(Array)
      items_before_filter = results["items"].length
      results["items"] = results["items"].map { |item| enhance_item_with_matching(item) }

      # Filter items based on user's gender preference
      results["items"] = filter_by_user_preference(results["items"])

      items_after_filter = results["items"].length
      if items_before_filter > items_after_filter
        Rails.logger.info "Filtered #{items_before_filter - items_after_filter} items based on user gender preference (#{user.gender_preference})"
      end
    end

    # Update total_items_detected after filtering
    results["total_items_detected"] = results["items"].length

    Rails.logger.info "Clothing detection completed: #{results['total_items_detected']} items detected for user #{user.id} (preference: #{user.gender_preference})"

    # Create analysis record
    analysis = create_analysis_record(results)

    # Return structured data with analysis ID
    results.merge("analysis_id" => analysis.id)
  rescue ArgumentError => e
    Rails.logger.error "Invalid arguments for clothing detection: #{e.message}"
    {
      "error" => "Invalid request: #{e.message}",
      "items" => [],
      "total_items_detected" => 0
    }
  rescue StandardError => e
    Rails.logger.error "Failed to analyze clothing detection: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")
    {
      "error" => "Analysis failed: #{e.message}",
      "items" => [],
      "total_items_detected" => 0
    }
  end

  private

  # Check Ollama availability - reuse logic from OutfitPhotoAnalyzer
  def check_ollama_availability!
    ollama_base = ENV["OLLAMA_API_BASE"] || "http://localhost:11434"
    base_uri = URI(ollama_base)

    Rails.logger.info "Checking Ollama availability at #{ollama_base}..."

    begin
      http = Net::HTTP.new(base_uri.host, base_uri.port)
      http.open_timeout = 10  # Increased from 3s - allow time for Ollama to start processing
      http.read_timeout = 120  # Increased from 3s - AI vision models need time to analyze images

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
    prompt = DETECTION_PROMPT

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
        temp_file = Tempfile.new([ "clothing_detection", extension ])
        temp_file.binmode
        image_data = image_blob.download
        temp_file.write(image_data)
        temp_file.flush

        # Validate image is not empty or corrupted
        if image_data.blank? || image_data.length < 100
          temp_file.close
          temp_file.unlink
          raise StandardError, "Image file is too small or corrupted (size: #{image_data&.length || 0} bytes)"
        end

        image_path = temp_file.path
      end

      # Validate image file exists and has reasonable size
      unless File.exist?(image_path) && File.size(image_path) > 100
        raise StandardError, "Image file is missing or too small to process"
      end

      # Use RubyLLM's 'with:' parameter to pass the image file path
      # Retry logic with exponential backoff for network timeouts
      max_retries = 3
      retry_count = 0
      assistant_message = nil

      begin
        assistant_message = chat.ask(prompt, with: image_path)
      rescue Net::ReadTimeout, Net::OpenTimeout, Errno::ECONNRESET => e
        retry_count += 1
        if retry_count <= max_retries
          wait_time = 2 ** retry_count # Exponential backoff: 2s, 4s, 8s
          Rails.logger.warn "Network timeout (attempt #{retry_count}/#{max_retries}), retrying in #{wait_time}s: #{e.class.name}"
          sleep(wait_time)
          retry
        else
          Rails.logger.error "Network timeout after #{max_retries} retries: #{e.message}"
          raise StandardError, "AI analysis timed out after #{max_retries} retries. Ollama may be overloaded or the image may be too complex."
        end
      end

      # Clean up temp file if we created one
      if temp_file
        temp_file.close
        temp_file.unlink
      end

      unless assistant_message&.content.present?
        raise StandardError, "Empty response from AI model"
      end

      # Parse the response into structured data
      parsed_results = parse_analysis_response(assistant_message.content)

      # Log detection results for debugging
      Rails.logger.info "Clothing detection raw response length: #{assistant_message.content.length} chars"
      Rails.logger.info "Parsed items count: #{parsed_results['items']&.length || 0}"
      if parsed_results["items"]&.any?
        Rails.logger.info "First item: #{parsed_results['items'].first&.dig('item_name')} (#{parsed_results['items'].first&.dig('gender_styling')})"
      end

      parsed_results
    rescue ArgumentError => e
      Rails.logger.error "Invalid arguments for chat.ask: #{e.message}"
      raise e
    rescue StandardError => e
      Rails.logger.error "Error during RubyLLM analysis: #{e.message}"
      if e.message.include?("connection") || e.message.include?("refused")
        raise StandardError, "Ollama service unavailable. Please ensure Ollama is running."
      end
      raise e
    ensure
      # Ensure temp file cleanup even if error occurs
      if temp_file
        temp_file.close rescue nil
        temp_file.unlink rescue nil
      end
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
      m.family = "qwen"
    end

    Chat.create!(
      user: user,
      model: model
    ).tap do |chat|
      Rails.logger.info "Created chat #{chat.id} for clothing detection analysis"
    end
  end

  def parse_analysis_response(content)
    # Extract JSON from response, handling AI's explanatory text
    # Strategy: Find the first valid JSON object that parses successfully

    # First, try to find JSON between first { and last }
    first_brace = content.index("{")
    last_brace = content.rindex("}")

    if first_brace && last_brace && first_brace < last_brace
      json_candidate = content[first_brace..last_brace]

      # Try parsing this candidate
      begin
        parsed = JSON.parse(json_candidate)
        return format_parsed_results(parsed)
      rescue JSON::ParserError => e
        Rails.logger.debug "First attempt failed: #{e.message}, trying alternative extraction"
      end
    end

    # Fallback: Try to extract JSON using code fence markers (```json ... ```)
    if content.include?("```json") || content.include?("```")
      json_match = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/m)
      if json_match
        begin
          parsed = JSON.parse(json_match[1])
          return format_parsed_results(parsed)
        rescue JSON::ParserError
          # Continue to next strategy
        end
      end
    end

    # Last resort: Find lines that look like JSON (start with { or end with })
    # and try to reconstruct the JSON object
    json_lines = []
    in_json = false
    brace_count = 0

    content.each_line do |line|
      # Start capturing when we see an opening brace at start of line (trimmed)
      if !in_json && line.strip.start_with?("{")
        in_json = true
        json_lines = []
      end

      if in_json
        json_lines << line
        brace_count += line.count("{") - line.count("}")

        # Stop when braces are balanced
        if brace_count == 0
          json_str = json_lines.join
          begin
            parsed = JSON.parse(json_str)
            return format_parsed_results(parsed)
          rescue JSON::ParserError
            # Reset and continue looking
            in_json = false
            json_lines = []
            brace_count = 0
          end
        end
      end
    end

    # If all extraction strategies failed
    Rails.logger.warn "Could not parse JSON from AI response. First 300 chars: #{content[0...300]}"
    {
      "items" => [],
      "total_items_detected" => 0,
      "people_count" => 0,
      "parse_error" => true,
      "error" => "Could not extract valid JSON from response"
    }
  rescue JSON::ParserError => e
    Rails.logger.error "JSON parse error: #{e.message}"
    Rails.logger.debug "Problematic content: #{content[0...500]}"
    {
      "items" => [],
      "total_items_detected" => 0,
      "people_count" => 0,
      "parse_error" => true,
      "error" => e.message
    }
  end

  def format_parsed_results(parsed)
    # Ensure items array exists
    parsed["items"] ||= []
    parsed["total_items_detected"] = parsed["items"].length
    parsed["people_count"] ||= 0

    # Ensure each item has required fields
    parsed["items"] = parsed["items"].map do |item|
      item["id"] ||= "item_#{SecureRandom.hex(4)}"
      item["confidence"] ||= 0.5
      item["gender_styling"] ||= "unisex" # Default to unisex if not specified
      item["extraction_priority"] ||= "medium"
      item["pattern_type"] ||= "solid"
      item["style_category"] ||= "casual"
      item
    end

    parsed
  end

  def validate_and_enhance_results(results)
    # Validate gender_styling values
    if results["items"].is_a?(Array)
      results["items"] = results["items"].map do |item|
        # Ensure gender_styling is valid
        unless %w[men women unisex].include?(item["gender_styling"])
          Rails.logger.warn "Invalid gender_styling '#{item["gender_styling"]}', defaulting to 'unisex'"
          item["gender_styling"] = "unisex"
        end

        # Ensure extraction_priority is valid
        unless %w[high medium low].include?(item["extraction_priority"])
          item["extraction_priority"] = "medium"
        end

        # Ensure confidence is in valid range
        if item["confidence"].present?
          item["confidence"] = [ 0.0, [ 1.0, item["confidence"].to_f ].min ].max
        end

        item
      end

      # POST-PROCESSING DEDUPLICATION: Remove duplicate items based on similarity
      results["items"] = deduplicate_detected_items(results["items"])
      results["total_items_detected"] = results["items"].length
    end

    results
  end

  # Deduplicate detected items based on name and category similarity
  # This is a safety net in case the AI model returns the same item multiple times
  def deduplicate_detected_items(items)
    return items if items.empty?

    unique_items = []
    seen_items = []

    items.each do |item|
      # Extract key attributes
      name = (item["item_name"] || item[:item_name] || "").downcase.strip
      category = (item["category"] || item[:category] || "").downcase.strip
      color = (item["color_primary"] || item[:color_primary] || "").downcase.strip

      # Normalize name by removing common descriptive words
      normalized_name = name
        .gsub(/\b(light|dark|colored|patterned|long|short)\b/, "")
        .gsub(/\b(dress|shirt|top|blouse|polo)\b/, "garment") # Treat similar tops as same base type
        .gsub(/\s+/, " ")
        .strip

      # Check for duplicates by comparing with already seen items
      is_duplicate = seen_items.any? do |seen|
        seen_name = seen[:normalized_name]
        seen_category = seen[:category]
        seen_color = seen[:color]

        # Same if: Same category AND same color AND similar name
        same_category = category == seen_category || (category == "tops" && seen_category == "tops")
        same_color = color == seen_color

        # Check name similarity using multiple strategies:
        # 1. Exact match after normalization
        # 2. One name contains the other
        # 3. Significant word overlap (at least 60% of words match)
        similar_name = false
        if normalized_name.present? && seen_name.present?
          similar_name = (normalized_name == seen_name) ||
                         (normalized_name.include?(seen_name)) ||
                         (seen_name.include?(normalized_name)) ||
                         (word_overlap_percentage(normalized_name, seen_name) >= 0.6)
        end

        same_category && same_color && similar_name
      end

      if is_duplicate
        Rails.logger.info "DEDUPLICATION: Skipping duplicate item '#{name}' (similar to existing item)"
        next
      end

      seen_items << { normalized_name: normalized_name, category: category, color: color, original_name: name }
      unique_items << item
    end

    if unique_items.length < items.length
      Rails.logger.info "DEDUPLICATION: Removed #{items.length - unique_items.length} duplicate items from detection results"
    end

    unique_items
  end

  # Calculate percentage of word overlap between two strings
  def word_overlap_percentage(str1, str2)
    words1 = str1.split
    words2 = str2.split

    return 1.0 if words1 == words2
    return 0.0 if words1.empty? || words2.empty?

    # Find common words
    common_words = (words1 & words2).length
    smaller_set_size = [ words1.length, words2.length ].min

    common_words.to_f / smaller_set_size
  end

  def filter_by_user_preference(items)
    return items unless user.gender_preference.present?

    user_pref = user.gender_preference.downcase

    # If user prefers "unisex", show all items (no filtering)
    return items if user_pref == "unisex"

    # For "men" or "women" preference: show matching items + unisex items
    items.select do |item|
      item_gender = (item["gender_styling"] || "unisex").downcase
      item_gender == user_pref || item_gender == "unisex"
    end
  end

  def enhance_item_with_matching(item_data)
    # Match category from database (using category field from detection)
    if item_data["category"].present?
      matched_category = find_matching_category(item_data["category"])
      item_data["category_id"] = matched_category&.id
      item_data["category_matched"] = matched_category&.name
      item_data["category_name"] = item_data["category"] # Keep original for reference
    end

    # Note: Brand matching would go here if we had brand_name in detection results
    # For now, clothing detection doesn't extract brands

    # Generate extraction_prompt for ComfyUI stock photo extraction
    generate_extraction_prompt_for_item(item_data)

    item_data
  end

  def generate_extraction_prompt_for_item(item_data)
    # Only generate prompt if we have valid item data
    return if item_data["error"].present? || item_data["parse_error"]

    begin
      prompt_builder = Services::ExtractionPromptBuilder.new(
        item_data: item_data,
        user: user
      )

      item_data["extraction_prompt"] = prompt_builder.build_prompt
      Rails.logger.info "Generated extraction prompt for detected item: #{item_data['item_name']}"
    rescue StandardError => e
      Rails.logger.warn "Failed to generate extraction prompt for item: #{e.message}"
      # Don't fail the entire detection if prompt generation fails
      item_data["extraction_prompt"] = nil
    end
  end

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

  def create_analysis_record(results)
    # Calculate average confidence
    # - Missing confidence key: treat as 0.0 (item was detected but no confidence provided)
    # - Explicit nil: exclude from calculation (confidence measurement failed/unavailable)
    items = results["items"] || []
    confidences = items.map do |item|
      if item.key?("confidence")
        item["confidence"] # Could be a number or nil
      else
        0.0 # Missing key means no confidence provided, treat as 0.0
      end
    end.compact # Remove explicit nils
    avg_confidence = confidences.any? ? (confidences.sum.to_f / confidences.length).round(2) : nil

    ClothingAnalysis.create!(
      user: user,
      image_blob_id: image_blob.id,
      parsed_data: results,
      items_detected: results["total_items_detected"] || 0,
      confidence: avg_confidence,
      status: results["error"] ? "failed" : "completed"
    )
  end
end
