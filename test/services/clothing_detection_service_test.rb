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
end
