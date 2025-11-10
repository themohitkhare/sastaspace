# Service for detecting multiple clothing items in a single image
# Uses RubyLLM with Qwen3-VL model via Ollama
class ClothingDetectionService
  attr_reader :image_blob, :user, :model_name

  DETECTION_PROMPT = <<~PROMPT
    CLOTHING DETECTION FOR SASTASPACE INVENTORY

    Analyze this image and identify ALL clothing and fashion items visible on all people. Return only valid JSON.

    {
      "total_items_detected": number,
      "people_count": number,
      "items": [
        {
          "id": "item_001",
          "item_name": "specific name",
          "category": "tops/bottoms/outerwear/shoes/accessories",
          "subcategory": "shirt/jeans/jacket/sneakers",
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
    - Detect ALL visible items: clothing (tops, bottoms, outerwear), shoes, bags, accessories, jewelry, etc.
    - gender_styling MUST be one of: "men", "women", or "unisex" for each item
    - extraction_priority should reflect how important/visible each item is
    - confidence should reflect how certain you are about each item's analysis
    - Include at least 2-3 items minimum if multiple items are visible
    - Be thorough but accurate - don't invent items that aren't clearly visible
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
    # Try to extract JSON from the response
    json_match = content.match(/\{[\s\S]*\}/m)

    if json_match
      parsed = JSON.parse(json_match[0])

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
    else
      Rails.logger.warn "Could not parse JSON from AI response: #{content.truncate(200)}"
      {
        "items" => [],
        "total_items_detected" => 0,
        "people_count" => 0,
        "parse_error" => true,
        "error" => "Could not parse response"
      }
    end
  rescue JSON::ParserError => e
    Rails.logger.error "JSON parse error: #{e.message}"
    {
      "items" => [],
      "total_items_detected" => 0,
      "people_count" => 0,
      "parse_error" => true,
      "error" => e.message
    }
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
    end

    results
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

    item_data
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
    items = results["items"] || []
    confidences = items.map { |item| item["confidence"] || 0.0 }.compact
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
