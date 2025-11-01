require "test_helper"

module Services
  class OutfitPhotoAnalyzerTest < ActiveSupport::TestCase
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
      @analyzer = OutfitPhotoAnalyzer.new(
        image_blob: @image_blob,
        user: @user,
        model_name: "qwen3-vl:8b"
      )
    end

    test "analyze returns array of detected items" do
      # Skip if Ollama not available
      skip "Set ENABLE_OLLAMA_TESTS=true and ensure Ollama is running to test with real Ollama" unless ollama_available?

      results = @analyzer.analyze

      assert results.is_a?(Hash), "Results should be a Hash, got: #{results.class}"
      assert results["items"].is_a?(Array), "Results should include items array"
      assert results["total_items"].present?, "Results should include total_items count"

      if results["error"].present?
        flunk "Analysis failed with error: #{results['error']}. Results: #{results.inspect}"
      end

      # For outfit photos, we expect multiple items
      assert results["total_items"] > 0, "Should detect at least one item in outfit photo"
    end

    test "analyze handles missing image blob gracefully" do
      analyzer = OutfitPhotoAnalyzer.new(
        image_blob: nil,
        user: @user,
        model_name: "qwen3-vl:8b"
      )

      results = analyzer.analyze

      assert results["error"].present?
      assert_equal 0, results["total_items"]
      assert_equal [], results["items"]
    end

    test "parse_analysis_response extracts JSON array from response" do
      json_content = {
        "total_items" => 2,
        "items" => [
          {
            "category_name" => "T-Shirt",
            "name" => "Blue Cotton T-Shirt",
            "description" => "A blue cotton t-shirt",
            "brand_name" => nil,
            "position" => "top",
            "confidence" => 0.9
          },
          {
            "category_name" => "Jeans",
            "name" => "Blue Denim Jeans",
            "description" => "Blue denim jeans",
            "brand_name" => nil,
            "position" => "bottom",
            "confidence" => 0.85
          }
        ]
      }.to_json

      result = @analyzer.send(:parse_analysis_response, "Some text #{json_content} more text")

      assert_equal 2, result["total_items"]
      assert_equal 2, result["items"].length
      assert_equal "T-Shirt", result["items"][0]["category_name"]
      assert_equal "Jeans", result["items"][1]["category_name"]
    end

    test "parse_analysis_response handles empty items array" do
      json_content = {
        "total_items": 0,
        "items": []
      }.to_json

      result = @analyzer.send(:parse_analysis_response, json_content)

      assert_equal 0, result["total_items"]
      assert_equal [], result["items"]
    end

    test "parse_analysis_response uses fallback when no JSON found" do
      text = "This is just plain text without any JSON"
      result = @analyzer.send(:parse_analysis_response, text)

      assert_equal 0, result["total_items"]
      assert_equal [], result["items"]
      assert result["parse_error"]
      assert result["error"].present?
    end

    test "parse_analysis_response sets default values for items" do
      json_content = {
        "total_items": 1,
        "items": [
          {
            "category_name": "T-Shirt",
            "name": "Test Item"
          }
        ]
      }.to_json

      result = @analyzer.send(:parse_analysis_response, json_content)

      item = result["items"].first
      assert_equal 0.5, item["confidence"]
      assert_equal "No description available", item["description"]
      assert_equal "unknown", item["position"]
    end

    test "enhance_item_with_matching adds category_id and brand_id" do
      category_name = "T-Shirt #{SecureRandom.hex(4)}"
      brand_name = "Nike #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      brand = create(:brand, name: brand_name)

      item_data = {
        "category_name" => category_name,
        "brand_name" => brand_name,
        "description" => "A blue cotton t-shirt",
        "name" => "Blue T-Shirt",
        "confidence" => 0.9
      }

      enhanced = @analyzer.send(:enhance_item_with_matching, item_data)

      assert_equal category.id, enhanced["category_id"]
      assert_equal brand.id, enhanced["brand_id"]
      assert_equal category_name, enhanced["category_matched"]
      assert_equal brand_name, enhanced["brand_matched"]
    end

    test "enhance_item_with_matching handles missing category_name" do
      item_data = {
        "brand_name" => "Nike",
        "description" => "Test",
        "name" => "Test Item"
      }

      enhanced = @analyzer.send(:enhance_item_with_matching, item_data)

      assert_nil enhanced["category_id"]
      assert_nil enhanced["category_matched"]
    end

    test "enhance_item_with_matching handles missing brand_name" do
      item_data = {
        "category_name" => "T-Shirt",
        "description" => "Test",
        "name" => "Test Item"
      }

      enhanced = @analyzer.send(:enhance_item_with_matching, item_data)

      assert_nil enhanced["brand_id"]
      assert_nil enhanced["brand_matched"]
    end

    test "analyze enhances all items with matching" do
      category_name = "T-Shirt #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)

      # Mock the analysis to return items
      mock_chat = stub
      json_content = {
        "total_items": 1,
        "items": [
          {
            "category_name" => category_name,
            "name" => "Test Item",
            "description" => "Test description",
            "confidence" => 0.9
          }
        ]
      }.to_json

      mock_message = stub(content: json_content)
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)

      results = @analyzer.analyze

      assert_equal 1, results["total_items"]
      assert_equal 1, results["items"].length
      assert_equal category.id, results["items"].first["category_id"]
    end

    test "analyze handles StandardError gracefully" do
      @analyzer.stubs(:check_ollama_availability!).raises(StandardError, "Test error")

      results = @analyzer.analyze

      assert results["error"].present?
      assert_includes results["error"], "Analysis failed"
      assert_equal 0, results["total_items"]
      assert_equal [], results["items"]
    end

    test "check_ollama_availability! raises error when Ollama is unreachable" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(Errno::ECONNREFUSED)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! succeeds when model exists" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => "qwen3-vl:8b" } ] }.to_json
      )

      assert_nothing_raised do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "find_matching_category works for outfit analyzer" do
      category_name = "T-Shirt #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      result = @analyzer.send(:find_matching_category, category_name)

      assert_equal category, result
    end

    test "find_matching_brand works for outfit analyzer" do
      brand_name = "Nike #{SecureRandom.hex(4)}"
      brand = create(:brand, name: brand_name)
      result = @analyzer.send(:find_matching_brand, brand_name)

      assert_equal brand, result
    end

    test "analysis_prompt includes available categories" do
      tshirts_name = "T-Shirts #{SecureRandom.hex(4)}"
      jeans_name = "Jeans #{SecureRandom.hex(4)}"

      create(:category, name: tshirts_name, active: true)
      create(:category, name: jeans_name, active: true)

      prompt = @analyzer.send(:analysis_prompt)

      assert_includes prompt, tshirts_name
      assert_includes prompt, jeans_name
      assert_includes prompt, "complete outfit"
      assert_includes prompt, "Detect and extract information for EACH separate item"
      assert_includes prompt, "ALL individual clothing items"
    end

    test "perform_analysis handles image path correctly" do
      mock_chat = stub
      json_content = {
        "total_items": 2,
        "items": [
          { "category_name" => "T-Shirt", "name" => "Test", "description" => "Test", "confidence" => 0.9 },
          { "category_name" => "Jeans", "name" => "Test", "description" => "Test", "confidence" => 0.85 }
        ]
      }.to_json

      mock_message = stub(content: json_content)
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)

      result = @analyzer.send(:perform_analysis)

      assert result.is_a?(Hash)
      assert_equal 2, result["total_items"]
      assert_equal 2, result["items"].length
    end

    private

    def stub_ollama_available
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => "qwen3-vl:8b" } ] }.to_json
      )
    end
  end
end
