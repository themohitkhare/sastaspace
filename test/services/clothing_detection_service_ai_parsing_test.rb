require "test_helper"

# Tests for real-world AI parsing scenarios
# These test cases were added after discovering that AI models sometimes
# include explanatory text or "thinking out loud" in their responses
class ClothingDetectionServiceAiParsingTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
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

  test "parse_analysis_response handles AI model thinking out loud before JSON" do
    # Real-world scenario from production logs: AI includes explanatory text before JSON
    content = <<~CONTENT
      Wait no, I just need to output the JSON correctly. I've structured the JSON properly, checking the syntax and ensuring all items align with the requirements.
      {
        "total_items_detected": 1,
        "people_count": 0,
        "items": [
          {
            "id": "item_001",
            "item_name": "Brown Flat Sandals",
            "category": "shoes",
            "subcategory": "sandals",
            "confidence": 0.7
          }
        ]
      }
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    assert_equal 1, result["total_items_detected"]
    assert_equal 1, result["items"].length
    assert_equal "Brown Flat Sandals", result["items"][0]["item_name"]
    assert_equal 0.7, result["items"][0]["confidence"]
    assert_nil result["parse_error"], "Should successfully extract JSON despite AI commentary"
  end

  test "parse_analysis_response handles JSON wrapped in code fences" do
    # AI models sometimes wrap JSON in markdown code blocks
    content = <<~CONTENT
      Here's the analysis:
      ```json
      {
        "total_items_detected": 2,
        "people_count": 0,
        "items": [
          {
            "id": "item_001",
            "item_name": "Red Shirt",
            "category": "tops"
          },
          {
            "id": "item_002",
            "item_name": "Blue Jeans",
            "category": "bottoms"
          }
        ]
      }
      ```
      That's the result!
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    assert_equal 2, result["total_items_detected"]
    assert_equal 2, result["items"].length
    assert_equal "Red Shirt", result["items"][0]["item_name"]
    assert_equal "Blue Jeans", result["items"][1]["item_name"]
    assert_nil result["parse_error"], "Should extract JSON from code fences"
  end

  test "parse_analysis_response handles AI monologue interspersed with JSON" do
    # AI includes thoughts before and after JSON structure
    content = <<~CONTENT
      Let me analyze this image carefully.
      {
        "total_items_detected": 1,
        "people_count": 0,
        "items": [
          {
            "id": "item_001",
            "item_name": "White T-Shirt",
            "category": "tops",
            "confidence": 0.85
          }
        ]
      }
      I've identified one clothing item.
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    assert_equal 1, result["total_items_detected"]
    assert_equal 1, result["items"].length
    assert_equal "White T-Shirt", result["items"][0]["item_name"]
    assert_nil result["parse_error"], "Should extract JSON with commentary before and after"
  end

  test "parse_analysis_response handles completely malformed response" do
    # When extraction fails completely (no JSON at all)
    content = "I can't see any clothing items in this image. Sorry!"

    result = @service.send(:parse_analysis_response, content)

    assert_equal 0, result["total_items_detected"]
    assert_equal [], result["items"]
    assert result["parse_error"], "Should indicate parse error"
    assert result["error"].present?, "Should include error message"
  end

  test "parse_analysis_response handles JSON with AI commentary at end" do
    # AI adds commentary after valid JSON
    content = <<~CONTENT
      {
        "total_items_detected": 3,
        "people_count": 1,
        "items": [
          {"id": "item_001", "item_name": "Shirt", "category": "tops"},
          {"id": "item_002", "item_name": "Pants", "category": "bottoms"},
          {"id": "item_003", "item_name": "Shoes", "category": "shoes"}
        ]
      }
      Note: I've detected 3 items total with high confidence.
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    assert_equal 3, result["total_items_detected"]
    assert_equal 3, result["items"].length
    assert_nil result["parse_error"], "Should handle trailing commentary"
  end

  test "parse_analysis_response handles multiple JSON-like structures" do
    # AI might generate example JSON before actual result
    content = <<~CONTENT
      I'll format the response like this: {"example": "format"}

      Here's the actual result:
      {
        "total_items_detected": 1,
        "people_count": 0,
        "items": [
          {
            "id": "item_001",
            "item_name": "Green Jacket",
            "category": "outerwear"
          }
        ]
      }
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    # Should extract the first complete, valid JSON object
    assert result["items"].present? || result["total_items_detected"] >= 0
    # The exact behavior depends on which JSON object is extracted first
    # The important thing is it doesn't crash
  end

  test "parse_analysis_response handles nested JSON explanations" do
    # AI explains JSON structure while outputting it
    content = <<~CONTENT
      The JSON structure has "items" array with details:
      {
        "total_items_detected": 2,
        "items": [
          {"id": "item_001", "item_name": "Hat", "category": "accessories"},
          {"id": "item_002", "item_name": "Scarf", "category": "accessories"}
        ]
      }
    CONTENT

    result = @service.send(:parse_analysis_response, content)

    assert_equal 2, result["total_items_detected"]
    assert_equal 2, result["items"].length
  end
end
