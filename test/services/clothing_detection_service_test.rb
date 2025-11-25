require "test_helper"

class ClothingDetectionServiceTest < ActiveSupport::TestCase
  # Helper to check if Ollama is available
  def ollama_available?
    return false unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    begin
      uri = URI(ENV["OLLAMA_API_BASE"] || "http://localhost:11434")
      http = Net::HTTP.new(uri.host, uri.port)
      http.open_timeout = 2
      http.read_timeout = 2
      response = http.get("/api/tags")
      response.code == "200"
    rescue StandardError
      false
    end
  end

  def setup
    @user = create(:user)
    # Use clothing_outfit_1.jpg which is a proper clothing photo (800x1107)
    # sample_image.jpg is only 1x1 pixel and may be corrupted
    image_path = Rails.root.join("test/fixtures/files/clothing_outfit_1.jpg")
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(image_path),
      filename: "clothing_outfit_1.jpg",
      content_type: "image/jpeg"
    )
    @service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: @user,
      model_name: "qwen3-vl:8b"
    )
  end

  test "analyze handles missing image blob gracefully" do
    service = ClothingDetectionService.new(
      image_blob: nil,
      user: @user,
      model_name: "qwen3-vl:8b"
    )

    results = service.analyze

    assert results["error"].present?
    assert_equal 0, results["total_items_detected"]
    assert_equal [], results["items"]
  end

  test "analyze handles missing user gracefully" do
    service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: nil,
      model_name: "qwen3-vl:8b"
    )

    results = service.analyze

    assert results["error"].present?
  end

  test "parse_analysis_response extracts JSON from response" do
    json_content = {
      "total_items_detected" => 3,
      "people_count" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Blue Shirt",
          "category" => "tops",
          "subcategory" => "shirt",
          "color_primary" => "blue",
          "pattern_type" => "solid",
          "material_type" => "cotton",
          "style_category" => "casual",
          "gender_styling" => "men",
          "extraction_priority" => "high",
          "confidence" => 0.9
        },
        {
          "id" => "item_002",
          "item_name" => "Black Jeans",
          "category" => "bottoms",
          "subcategory" => "jeans",
          "color_primary" => "black",
          "pattern_type" => "solid",
          "material_type" => "denim",
          "style_category" => "casual",
          "gender_styling" => "unisex",
          "extraction_priority" => "medium",
          "confidence" => 0.85
        },
        {
          "id" => "item_003",
          "item_name" => "White Sneakers",
          "category" => "shoes",
          "subcategory" => "sneakers",
          "color_primary" => "white",
          "pattern_type" => "solid",
          "material_type" => "synthetic",
          "style_category" => "casual",
          "gender_styling" => "unisex",
          "extraction_priority" => "low",
          "confidence" => 0.8
        }
      ]
    }.to_json

    result = @service.send(:parse_analysis_response, "Some text #{json_content} more text")

    assert_equal 3, result["total_items_detected"]
    assert_equal 1, result["people_count"]
    assert_equal 3, result["items"].length
    assert_equal "Blue Shirt", result["items"][0]["item_name"]
    assert_equal "men", result["items"][0]["gender_styling"]
    assert_equal "unisex", result["items"][1]["gender_styling"]
  end

  test "parse_analysis_response sets default values for missing fields" do
    json_content = {
      "total_items_detected" => 1,
      "people_count" => 1,
      "items" => [
        {
          "item_name" => "Test Item",
          "category" => "tops"
        }
      ]
    }.to_json

    result = @service.send(:parse_analysis_response, json_content)

    item = result["items"].first
    assert item["id"].present?
    assert_equal 0.5, item["confidence"]
    assert_equal "unisex", item["gender_styling"] # Default
    assert_equal "medium", item["extraction_priority"] # Default
    assert_equal "solid", item["pattern_type"] # Default
    assert_equal "casual", item["style_category"] # Default
  end

  test "parse_analysis_response handles empty items array" do
    json_content = {
      "total_items_detected" => 0,
      "people_count" => 0,
      "items" => []
    }.to_json

    result = @service.send(:parse_analysis_response, json_content)

    assert_equal 0, result["total_items_detected"]
    assert_equal 0, result["people_count"]
    assert_equal [], result["items"]
  end

  test "parse_analysis_response uses fallback when no JSON found" do
    text = "This is just plain text without any JSON"
    result = @service.send(:parse_analysis_response, text)

    assert_equal 0, result["total_items_detected"]
    assert_equal 0, result["people_count"]
    assert_equal [], result["items"]
    assert result["parse_error"]
    assert result["error"].present?
  end

  test "validate_and_enhance_results validates gender_styling" do
    results = {
      "items" => [
        { "gender_styling" => "men", "confidence" => 0.9 },
        { "gender_styling" => "invalid", "confidence" => 0.8 },
        { "gender_styling" => "women", "confidence" => 0.85 }
      ]
    }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_equal "men", validated["items"][0]["gender_styling"]
    assert_equal "unisex", validated["items"][1]["gender_styling"] # Invalid value defaulted
    assert_equal "women", validated["items"][2]["gender_styling"]
  end

  test "validate_and_enhance_results validates extraction_priority" do
    results = {
      "items" => [
        { "extraction_priority" => "high", "confidence" => 0.9 },
        { "extraction_priority" => "invalid", "confidence" => 0.8 }
      ]
    }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_equal "high", validated["items"][0]["extraction_priority"]
    assert_equal "medium", validated["items"][1]["extraction_priority"] # Invalid value defaulted
  end

  test "validate_and_enhance_results clamps confidence to 0-1 range" do
    results = {
      "items" => [
        { "confidence" => 1.5 }, # Too high
        { "confidence" => -0.5 }, # Too low
        { "confidence" => 0.8 } # Valid
      ]
    }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_equal 1.0, validated["items"][0]["confidence"]
    assert_equal 0.0, validated["items"][1]["confidence"]
    assert_equal 0.8, validated["items"][2]["confidence"]
  end

  test "create_analysis_record creates ClothingAnalysis with correct data" do
    results = {
      "total_items_detected" => 2,
      "people_count" => 1,
      "items" => [
        { "confidence" => 0.9 },
        { "confidence" => 0.8 }
      ]
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_not_nil analysis.id
    assert_equal @user, analysis.user
    assert_equal @image_blob.id, analysis.image_blob_id
    assert_equal 2, analysis.items_detected
    assert_equal 0.85, analysis.confidence # Average of 0.9 and 0.8
    assert_equal "completed", analysis.status
  end

  test "create_analysis_record sets failed status when error present" do
    results = {
      "error" => "Test error",
      "total_items_detected" => 0,
      "items" => []
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_equal "failed", analysis.status
  end

  test "create_analysis_record handles nil confidence" do
    results = {
      "total_items_detected" => 0,
      "items" => []
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_nil analysis.confidence
  end

  test "analyze returns analysis_id in results" do
    # Stub the perform_analysis to avoid Ollama call
    @service.stubs(:check_ollama_availability!)
    @service.stubs(:perform_analysis).returns({
      "total_items_detected" => 2,
      "people_count" => 1,
      "items" => [
        { "id" => "item_001", "item_name" => "Shirt", "confidence" => 0.9 },
        { "id" => "item_002", "item_name" => "Pants", "confidence" => 0.8 }
      ]
    })

    results = @service.analyze

    assert results["analysis_id"].present?
    assert_equal 2, results["total_items_detected"]
    assert_equal 1, results["people_count"]
  end

  test "analyze with real Ollama" do
    skip "Set ENABLE_OLLAMA_TESTS=true and ensure Ollama is running to test with real Ollama" unless ollama_available?

    results = @service.analyze

    assert results.is_a?(Hash), "Results should be a Hash, got: #{results.class}"

    if results["error"].present?
      flunk "Analysis failed with error: #{results['error']}. Results: #{results.inspect}"
    end

    assert results["total_items_detected"].present?
    assert results["items"].is_a?(Array)
    assert results["analysis_id"].present?

    # Check gender_styling is present and valid
    if results["items"].any?
      results["items"].each do |item|
        assert_includes %w[men women unisex], item["gender_styling"], "Item #{item['item_name']} has invalid gender_styling: #{item['gender_styling']}"
      end
    end
  end

  test "gender_styling field is included in prompt" do
    prompt = ClothingDetectionService::DETECTION_PROMPT

    assert_includes prompt, "gender_styling"
    assert_includes prompt, "men"
    assert_includes prompt, "women"
    assert_includes prompt, "unisex"
    assert_includes prompt, "GENDER STYLING GUIDELINES"
  end

  test "filter_by_user_preference returns all items when preference is unisex" do
    @user.update(gender_preference: "unisex")
    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = @service.send(:filter_by_user_preference, items)

    assert_equal 3, filtered.length
  end

  test "filter_by_user_preference filters to men and unisex when preference is men" do
    @user.update(gender_preference: "men")
    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = @service.send(:filter_by_user_preference, items)

    assert_equal 2, filtered.length
    assert_includes filtered.map { |i| i["gender_styling"] }, "men"
    assert_includes filtered.map { |i| i["gender_styling"] }, "unisex"
    assert_not_includes filtered.map { |i| i["gender_styling"] }, "women"
  end

  test "filter_by_user_preference filters to women and unisex when preference is women" do
    @user.update(gender_preference: "women")
    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = @service.send(:filter_by_user_preference, items)

    assert_equal 2, filtered.length
    assert_includes filtered.map { |i| i["gender_styling"] }, "women"
    assert_includes filtered.map { |i| i["gender_styling"] }, "unisex"
    assert_not_includes filtered.map { |i| i["gender_styling"] }, "men"
  end

  test "filter_by_user_preference returns all items when no preference set" do
    @user.update(gender_preference: nil)
    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = @service.send(:filter_by_user_preference, items)

    assert_equal 3, filtered.length
  end

  test "filter_by_user_preference handles items without gender_styling" do
    @user.update(gender_preference: "men")
    items = [
      { "gender_styling" => "men" },
      {} # No gender_styling
    ]

    filtered = @service.send(:filter_by_user_preference, items)

    assert_equal 2, filtered.length # Both should pass (no gender_styling defaults to unisex)
  end

  test "enhance_item_with_matching adds category_id when category matches" do
    # Find or create category with exact name "Tops" to match the search
    category = Category.find_or_create_by(name: "Tops") do |c|
      c.description = "Test category"
      c.sort_order = 1
      c.active = true
    end
    item_data = { "category" => "tops" }

    enhanced = @service.send(:enhance_item_with_matching, item_data)

    assert_equal category.id, enhanced["category_id"]
    assert_equal category.name, enhanced["category_matched"]
    assert_equal "tops", enhanced["category_name"]
  end

  test "enhance_item_with_matching handles nil category" do
    item_data = { "category" => nil }

    enhanced = @service.send(:enhance_item_with_matching, item_data)

    assert_nil enhanced["category_id"]
    assert_nil enhanced["category_matched"]
  end

  test "enhance_item_with_matching handles blank category" do
    item_data = { "category" => "" }

    enhanced = @service.send(:enhance_item_with_matching, item_data)

    assert_nil enhanced["category_id"]
  end

  test "find_matching_category finds exact match" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")

    result = @service.send(:find_matching_category, "t-shirts")

    assert_equal category, result
  end

  test "find_matching_category finds synonym match" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")

    result = @service.send(:find_matching_category, "t-shirt")

    assert_equal category, result
  end

  test "find_matching_category finds word-based match" do
    category = create(:category, name: "Running Shoes #{SecureRandom.hex(4)}")

    result = @service.send(:find_matching_category, "running")

    assert_equal category, result
  end

  test "find_matching_category finds partial match" do
    category = create(:category, name: "Denim Jeans #{SecureRandom.hex(4)}")

    result = @service.send(:find_matching_category, "denim")

    assert_equal category, result
  end

  test "find_matching_category returns nil when no match" do
    result = @service.send(:find_matching_category, "nonexistent_category_xyz")

    assert_nil result
  end

  test "find_matching_category handles blank input" do
    result = @service.send(:find_matching_category, "")

    assert_nil result
  end

  test "find_matching_category handles nil input" do
    result = @service.send(:find_matching_category, nil)

    assert_nil result
  end

  test "check_ollama_availability! raises error when connection refused" do
    Net::HTTP.stubs(:new).raises(Errno::ECONNREFUSED.new("Connection refused"))
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      @service.send(:check_ollama_availability!)
    end
  end

  test "check_ollama_availability! raises error when timeout" do
    http_mock = mock
    http_mock.stubs(:open_timeout=)
    http_mock.stubs(:read_timeout=)
    http_mock.stubs(:get).raises(Net::ReadTimeout.new("Timeout"))
    Net::HTTP.stubs(:new).returns(http_mock)
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      @service.send(:check_ollama_availability!)
    end
  end

  test "perform_analysis retries on network timeout and succeeds" do
    skip "Requires Ollama setup" unless ollama_available?

    # Stub chat creation
    chat_mock = mock
    @service.stubs(:create_chat).returns(chat_mock)

    # First call times out, second succeeds
    message_mock = mock
    message_mock.stubs(:content).returns('{"items": [{"item_name": "shirt"}]}')

    call_count = 0
    chat_mock.stubs(:ask).with { |*args|
      call_count += 1
      if call_count == 1
        raise Net::ReadTimeout.new("Timeout")
      else
        message_mock
      end
    }

    Rails.logger.stubs(:warn)
    Object.any_instance.stubs(:sleep) # Don't actually sleep in tests

    result = @service.send(:perform_analysis)

    assert result.present?
    assert_equal 2, call_count, "Should have retried once after timeout"
  end

  test "perform_analysis fails after max retries on persistent timeout" do
    skip "Requires Ollama setup" unless ollama_available?

    # Stub chat creation
    chat_mock = mock
    @service.stubs(:create_chat).returns(chat_mock)

    # Always timeout
    chat_mock.stubs(:ask).raises(Net::ReadTimeout.new("Persistent timeout"))

    Rails.logger.stubs(:warn)
    Rails.logger.stubs(:error)
    Object.any_instance.stubs(:sleep) # Don't actually sleep in tests

    error = assert_raises(StandardError) do
      @service.send(:perform_analysis)
    end

    assert_includes error.message, "timed out after"
    assert_includes error.message, "retries"
  end

  test "check_ollama_availability! raises error when model not found" do
    http_mock = mock
    http_mock.stubs(:open_timeout=)
    http_mock.stubs(:read_timeout=)
    response_mock = mock
    response_mock.stubs(:code).returns("200")
    response_mock.stubs(:body).returns({ "models" => [] }.to_json)
    http_mock.stubs(:get).returns(response_mock)
    Net::HTTP.stubs(:new).returns(http_mock)
    Rails.logger.stubs(:warn)

    assert_raises(StandardError) do
      @service.send(:check_ollama_availability!)
    end
  end

  test "check_ollama_availability! raises error when API returns non-200" do
    http_mock = mock
    http_mock.stubs(:open_timeout=)
    http_mock.stubs(:read_timeout=)
    response_mock = mock
    response_mock.stubs(:code).returns("500")
    http_mock.stubs(:get).returns(response_mock)
    Net::HTTP.stubs(:new).returns(http_mock)
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      @service.send(:check_ollama_availability!)
    end
  end

  test "check_ollama_availability! handles JSON parse error" do
    http_mock = mock
    http_mock.stubs(:open_timeout=)
    http_mock.stubs(:read_timeout=)
    response_mock = mock
    response_mock.stubs(:code).returns("200")
    response_mock.stubs(:body).returns("invalid json")
    http_mock.stubs(:get).returns(response_mock)
    Net::HTTP.stubs(:new).returns(http_mock)
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      @service.send(:check_ollama_availability!)
    end
  end

  test "validate_and_enhance_results handles non-array items" do
    results = { "items" => "not an array" }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_equal "not an array", validated["items"]
  end

  test "validate_and_enhance_results handles nil items" do
    results = { "items" => nil }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_nil validated["items"]
  end

  test "validate_and_enhance_results handles confidence as string" do
    results = {
      "items" => [
        { "confidence" => "0.8" }
      ]
    }

    validated = @service.send(:validate_and_enhance_results, results)

    assert_equal 0.8, validated["items"][0]["confidence"]
  end

  test "create_analysis_record calculates average confidence correctly" do
    results = {
      "items" => [
        { "confidence" => 0.9 },
        { "confidence" => 0.7 },
        { "confidence" => 0.8 }
      ]
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_equal 0.8, analysis.confidence # (0.9 + 0.7 + 0.8) / 3 = 0.8
  end

  test "create_analysis_record handles items with nil confidence" do
    results = {
      "items" => [
        { "confidence" => 0.9 },
        { "confidence" => nil },
        { "confidence" => 0.8 }
      ]
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_equal 0.85, analysis.confidence # (0.9 + 0.0 + 0.8) / 3 = 0.566..., but we use compact so (0.9 + 0.8) / 2 = 0.85
  end

  test "analyze filters items by user preference" do
    @user.update(gender_preference: "men")
    @service.stubs(:check_ollama_availability!)
    @service.stubs(:perform_analysis).returns({
      "total_items_detected" => 3,
      "items" => [
        { "id" => "item_001", "gender_styling" => "men", "confidence" => 0.9 },
        { "id" => "item_002", "gender_styling" => "women", "confidence" => 0.8 },
        { "id" => "item_003", "gender_styling" => "unisex", "confidence" => 0.85 }
      ]
    })

    results = @service.analyze

    assert_equal 2, results["total_items_detected"]
    assert_equal 2, results["items"].length
    assert_includes results["items"].map { |i| i["gender_styling"] }, "men"
    assert_includes results["items"].map { |i| i["gender_styling"] }, "unisex"
    assert_not_includes results["items"].map { |i| i["gender_styling"] }, "women"
  end

  test "analyze enhances items with category matching" do
    # Find or create category with exact name "Tops" to match the search
    category = Category.find_or_create_by(name: "Tops") do |c|
      c.description = "Test category"
      c.sort_order = 1
      c.active = true
    end
    @service.stubs(:check_ollama_availability!)
    @service.stubs(:perform_analysis).returns({
      "total_items_detected" => 1,
      "items" => [
        { "id" => "item_001", "category" => "tops", "confidence" => 0.9 }
      ]
    })

    results = @service.analyze

    assert_equal category.id, results["items"].first["category_id"]
    assert_equal category.name, results["items"].first["category_matched"]
  end

  test "analyze handles StandardError and returns error response" do
    @service.stubs(:check_ollama_availability!).raises(StandardError.new("Test error"))
    Rails.logger.stubs(:error)

    results = @service.analyze

    assert results["error"].present?
    assert_equal 0, results["total_items_detected"]
    assert_equal [], results["items"]
  end

  test "analyze handles ArgumentError and returns error response" do
    @service.stubs(:check_ollama_availability!).raises(ArgumentError.new("Invalid argument"))
    Rails.logger.stubs(:error)

    results = @service.analyze

    assert results["error"].present?
    assert results["error"].include?("Invalid request")
    assert_equal 0, results["total_items_detected"]
  end

  test "parse_analysis_response handles JSON::ParserError" do
    invalid_json = '{"invalid": json}'
    Rails.logger.stubs(:error)

    result = @service.send(:parse_analysis_response, invalid_json)

    assert_equal 0, result["total_items_detected"]
    assert_equal [], result["items"]
    assert result["parse_error"]
    assert result["error"].present?
  end

  test "parse_analysis_response logs warning when no JSON found" do
    text = "Plain text without JSON"
    log_messages = []
    Rails.logger.stubs(:warn).with { |msg| log_messages << msg; true }

    result = @service.send(:parse_analysis_response, text)

    assert_equal 0, result["total_items_detected"]
    warn_log = log_messages.find { |msg| msg.include?("Could not parse JSON") }
    assert warn_log.present?, "Should log warning"
  end

  test "parse_analysis_response generates unique IDs for items without IDs" do
    json_content = {
      "items" => [
        { "item_name" => "Item 1" },
        { "item_name" => "Item 2" }
      ]
    }.to_json

    result = @service.send(:parse_analysis_response, json_content)

    assert result["items"][0]["id"].present?
    assert result["items"][1]["id"].present?
    assert_not_equal result["items"][0]["id"], result["items"][1]["id"]
  end

  test "create_analysis_record handles items without confidence" do
    results = {
      "items" => [
        { "item_name" => "Item 1" },
        { "item_name" => "Item 2", "confidence" => 0.8 }
      ]
    }

    analysis = @service.send(:create_analysis_record, results)

    assert_equal 0.4, analysis.confidence # (0.0 + 0.8) / 2 = 0.4
  end
end
