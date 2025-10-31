require "test_helper"

module Services
  class InventoryCreationAnalyzerTest < ActiveSupport::TestCase
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
      @image_blob = ActiveStorage::Blob.create_and_upload!(
        io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
        filename: "sample_image.jpg",
        content_type: "image/jpeg"
      )
      @analyzer = InventoryCreationAnalyzer.new(
        image_blob: @image_blob,
        user: @user,
        model_name: "qwen3-vl:8b"
      )
    end

    test "analyze returns structured data with category_id" do
      # Skip if Ollama not available
      skip "Set ENABLE_OLLAMA_TESTS=true and ensure Ollama is running to test with real Ollama" unless ollama_available?

      results = @analyzer.analyze

      assert results.is_a?(Hash), "Results should be a Hash, got: #{results.class}"

      if results["error"].present?
        flunk "Analysis failed with error: #{results['error']}. Results: #{results.inspect}"
      end

      # Focus on category matching - category_id should be present if category was matched
      assert results["category_name"].present?, "category_name should be present. Results: #{results.inspect}"
      # category_id may be nil if no exact match found, but category_name should exist
      assert results["confidence"].present?
      assert results["confidence"].is_a?(Numeric)
    end

    test "analyze handles missing image blob gracefully" do
      analyzer = InventoryCreationAnalyzer.new(
        image_blob: nil,
        user: @user,
        model_name: "qwen3-vl:8b"
      )

      results = analyzer.analyze

      assert results["error"].present?
      assert_equal 0.0, results["confidence"]
    end

    test "parse_analysis_response extracts JSON from response" do
      json_content = '{"category_name":"T-Shirt","name":"Blue Cotton T-Shirt","description":"A blue cotton t-shirt suitable for casual wear","brand_name":null,"confidence":0.9}'
      result = @analyzer.send(:parse_analysis_response, "Some text #{json_content} more text")

      assert_equal "T-Shirt", result["category_name"]
      assert_equal "Blue Cotton T-Shirt", result["name"]
      assert_equal "A blue cotton t-shirt suitable for casual wear", result["description"]
      assert_equal 0.9, result["confidence"]
    end

    test "parse_analysis_response uses fallback when no JSON found" do
      text = "This is just plain text without any JSON"
      result = @analyzer.send(:parse_analysis_response, text)

      # Fallback still sets item_type internally, but we focus on category_name
      assert_equal "Unidentified Item", result["name"]
      assert_equal 0.2, result["confidence"]
      assert result["parse_error"]
    end

    test "find_matching_category finds exact match" do
      category = create(:category, name: "T-Shirt")
      result = @analyzer.send(:find_matching_category, "T-Shirt")

      assert_equal category, result
    end

    test "find_matching_category finds fuzzy match" do
      category = create(:category, name: "T-Shirts")
      result = @analyzer.send(:find_matching_category, "T-Shirt")

      assert_equal category, result
    end

    test "find_matching_brand finds exact match" do
      brand = create(:brand, name: "Nike")
      result = @analyzer.send(:find_matching_brand, "Nike")

      assert_equal brand, result
    end

    test "enhance_with_matching adds category_id and brand_id" do
      category = create(:category, name: "T-Shirt")
      brand = create(:brand, name: "Nike")

      results = {
        "category_name" => "T-Shirt",
        "brand_name" => "Nike",
        "description" => "A blue cotton t-shirt",
        "name" => "Blue T-Shirt"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_equal category.id, enhanced["category_id"]
      assert_equal brand.id, enhanced["brand_id"]
      assert_equal "T-Shirt", enhanced["category_matched"]
      assert_equal "Nike", enhanced["brand_matched"]
    end

    test "prepare_image_data converts blob to base64 data URI" do
      image_data = @analyzer.send(:prepare_image_data)

      assert image_data.present?
      assert image_data.start_with?("data:image/jpeg;base64,")
    end
  end
end
