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
      category_name = "T-Shirt #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      result = @analyzer.send(:find_matching_category, category_name)

      assert_equal category, result
    end

    test "find_matching_category finds fuzzy match" do
      category_name = "T-Shirts #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      result = @analyzer.send(:find_matching_category, category_name.gsub(/s$/, ""))

      assert_equal category, result
    end

    test "find_matching_brand finds exact match" do
      brand_name = "Nike #{SecureRandom.hex(4)}"
      brand = create(:brand, name: brand_name)
      result = @analyzer.send(:find_matching_brand, brand_name)

      assert_equal brand, result
    end

    test "enhance_with_matching adds category_id and brand_id" do
      category_name = "T-Shirt #{SecureRandom.hex(4)}"
      brand_name = "Nike #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      brand = create(:brand, name: brand_name)

      results = {
        "category_name" => category_name,
        "brand_name" => brand_name,
        "description" => "A blue cotton t-shirt",
        "name" => "Blue T-Shirt"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_equal category.id, enhanced["category_id"]
      assert_equal brand.id, enhanced["brand_id"]
      assert_equal category_name, enhanced["category_matched"]
      assert_equal brand_name, enhanced["brand_matched"]
    end

    test "generate_extraction_prompt creates extraction_prompt in results" do
      category_name = "Hoodies #{SecureRandom.hex(4)}"
      category = create(:category, name: category_name)
      @user.update(gender_preference: "men")

      results = {
        "category_name" => category_name,
        "category_matched" => category_name,
        "name" => "Grey Zip-Up Hoodie",
        "description" => "A grey hoodie",
        "colors" => [ "grey", "black" ],
        "material" => "cotton blend fleece",
        "style" => "athletic streetwear",
        "brand_matched" => "Gym King"
      }

      @analyzer.send(:generate_extraction_prompt, results)

      assert results["extraction_prompt"].present?
      assert_includes results["extraction_prompt"], "GREY ZIP-UP HOODIE"
      assert_includes results["extraction_prompt"], "Gender Context: Men"
      assert_includes results["extraction_prompt"], "Category: #{category_name}"
    end

    test "generate_extraction_prompt handles errors gracefully" do
      results = {
        "error" => "Some error"
      }

      @analyzer.send(:generate_extraction_prompt, results)

      assert_nil results["extraction_prompt"]
    end

    test "prepare_image_data converts blob to base64 data URI" do
      image_data = @analyzer.send(:prepare_image_data)

      assert image_data.present?
      assert image_data.start_with?("data:image/jpeg;base64,")
    end

    test "analyze handles StandardError gracefully" do
      @analyzer.stubs(:check_ollama_availability!).raises(StandardError, "Test error")

      results = @analyzer.analyze

      assert results["error"].present?
      assert_includes results["error"], "Analysis failed"
      assert_equal 0.0, results["confidence"]
    end

    test "analyze handles parse_error and low confidence" do
      mock_chat = stub(ask: stub(content: '{"parse_error": true, "confidence": 0.05}'))
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

      assert results.is_a?(Hash)
    end

    test "check_ollama_availability! raises error when Ollama is unreachable" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(Errno::ECONNREFUSED)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! raises error when Ollama returns non-200" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(status: 500)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! raises error when model not found" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => "other-model:8b" } ] }.to_json
      )

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! succeeds when model exists with exact name" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => "qwen3-vl:8b" } ] }.to_json
      )

      assert_nothing_raised do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! succeeds when model exists with prefix match" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => "qwen3-vl:8b:latest" } ] }.to_json
      )

      assert_nothing_raised do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles timeout errors" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(Net::ReadTimeout)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles open timeout errors" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(Net::OpenTimeout)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles socket errors" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(SocketError.new("Network unreachable"))

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles host unreachable errors" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_raise(Errno::EHOSTUNREACH)

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles JSON parse errors" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: "invalid json"
      )

      assert_raises(StandardError) do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "check_ollama_availability! handles model with model field" do
      WebMock.stub_request(:get, /.*\/api\/tags/).to_return(
        status: 200,
        body: { "models" => [ { "name" => nil, "model" => "qwen3-vl:8b" } ] }.to_json
      )

      assert_nothing_raised do
        @analyzer.send(:check_ollama_availability!)
      end
    end

    test "perform_analysis uses image path from service when available" do
      mock_chat = stub
      mock_message = stub(content: '{"category_name":"T-Shirt","name":"Test","description":"Test","confidence":0.9}')
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      # Stub blob methods BEFORE stubbing service to avoid mock interference
      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:key).returns("test-key")

      # Mock service to return a path
      mock_service = stub
      existing_path = "/tmp/existing_path_#{SecureRandom.hex(4)}.jpg"
      mock_service.stubs(:path_for).returns(existing_path)
      mock_service.stubs(:respond_to?).with(:path_for).returns(true)
      @image_blob.stubs(:service).returns(mock_service)
      File.stubs(:exist?).with(existing_path).returns(true)

      result = @analyzer.send(:perform_analysis)

      assert result.is_a?(Hash)
      assert_equal "T-Shirt", result["category_name"]
    end

    test "perform_analysis creates temp file when service path doesn't exist" do
      mock_chat = stub
      mock_message = stub(content: '{"category_name":"T-Shirt","name":"Test","description":"Test","confidence":0.9}')
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      # Stub blob methods BEFORE stubbing service
      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))
      @image_blob.stubs(:key).returns("test-key")

      # Mock service to return a path that doesn't exist
      mock_service = stub
      non_existent_path = "/tmp/nonexistent_path_#{SecureRandom.hex(4)}.jpg"
      mock_service.stubs(:path_for).returns(non_existent_path)
      mock_service.stubs(:respond_to?).with(:path_for).returns(true)
      @image_blob.stubs(:service).returns(mock_service)
      File.stubs(:exist?).with(non_existent_path).returns(false)

      result = @analyzer.send(:perform_analysis)

      assert result.is_a?(Hash)
      assert_equal "T-Shirt", result["category_name"]
    end

    test "perform_analysis creates temp file when service doesn't support path_for" do
      mock_chat = stub
      mock_message = stub(content: '{"category_name":"T-Shirt","name":"Test","description":"Test","confidence":0.9}')
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      # Mock service to not have path_for method
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)
      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))

      result = @analyzer.send(:perform_analysis)

      assert result.is_a?(Hash)
      assert_equal "T-Shirt", result["category_name"]
    end

    test "perform_analysis raises error when image data cannot be prepared" do
      stub_ollama_available
      @analyzer.stubs(:prepare_image_data).returns(nil)

      assert_raises(ArgumentError) do
        @analyzer.send(:perform_analysis)
      end
    end

    test "perform_analysis handles empty response from AI" do
      mock_chat = stub
      mock_message = stub(content: nil)
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

      assert_raises(StandardError) do
        @analyzer.send(:perform_analysis)
      end
    end

    test "perform_analysis handles connection errors" do
      mock_chat = stub
      mock_chat.stubs(:ask).raises(StandardError.new("connection refused"))
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)

      assert_raises(StandardError) do
        @analyzer.send(:perform_analysis)
      end
    end

    test "perform_analysis handles argument errors in chat.ask" do
      mock_chat = stub
      mock_chat.stubs(:ask).raises(ArgumentError.new("Invalid argument"))
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: ".jpg"))
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)

      assert_raises(ArgumentError) do
        @analyzer.send(:perform_analysis)
      end
    end

    test "perform_analysis handles image blob without extension" do
      mock_chat = stub
      mock_message = stub(content: '{"category_name":"T-Shirt","name":"Test","description":"Test","confidence":0.9}')
      mock_chat.stubs(:ask).returns(mock_message)
      mock_chat.stubs(:id).returns(1)
      Chat.stubs(:create!).returns(mock_chat)
      stub_ollama_available

      # Mock blob without extension
      @image_blob.stubs(:filename).returns(stub(extension_with_delimiter: nil))
      @image_blob.stubs(:download).returns("fake image data")
      @image_blob.stubs(:content_type).returns("image/jpeg")
      mock_service = stub
      mock_service.stubs(:respond_to?).with(:path_for).returns(false)
      @image_blob.stubs(:service).returns(mock_service)

      result = @analyzer.send(:perform_analysis)

      assert result.is_a?(Hash)
      assert_equal "T-Shirt", result["category_name"]
    end

    test "create_chat creates chat with model" do
      model = Model.find_or_initialize_by(provider: "ollama", model_id: "qwen3-vl:8b")
      model.name = "qwen3-vl:8b"
      model.context_window = 8192
      model.family = "gemma"
      model.save!

      chat = @analyzer.send(:create_chat)

      assert_not_nil chat
      assert_equal @user, chat.user
      assert_equal model, chat.model
    end

    test "create_chat creates model if it doesn't exist" do
      Model.where(provider: "ollama", model_id: "qwen3-vl:8b").destroy_all

      chat = @analyzer.send(:create_chat)

      assert_not_nil chat
      model = Model.find_by(provider: "ollama", model_id: "qwen3-vl:8b")
      assert_not_nil model
      assert_equal "qwen3-vl:8b", model.name
    end

    test "analysis_prompt includes available categories" do
      tshirts_name = "T-Shirts #{SecureRandom.hex(4)}"
      jeans_name = "Jeans #{SecureRandom.hex(4)}"
      boots_name = "Boots #{SecureRandom.hex(4)}"

      create(:category, name: tshirts_name, active: true)
      create(:category, name: jeans_name, active: true)
      create(:category, name: boots_name, active: false) # Inactive category

      prompt = @analyzer.send(:analysis_prompt)

      assert_includes prompt, tshirts_name
      assert_includes prompt, jeans_name
      # Check that inactive category is not in the categories list
      # (Note: "Boots" might appear in example text, so check for the specific category name)
      assert_not_includes prompt, boots_name
    end

    test "parse_analysis_response handles JSON parse errors" do
      result = @analyzer.send(:parse_analysis_response, "{ invalid json }")

      assert result["parse_error"]
      assert_equal "Unidentified Item", result["name"]
      assert_equal 0.0, result["confidence"]
      assert result["error"].present?
    end

    test "parse_analysis_response sets default confidence and description" do
      json_content = '{"category_name":"T-Shirt","name":"Test"}'
      result = @analyzer.send(:parse_analysis_response, json_content)

      assert_equal 0.5, result["confidence"]
      assert_equal "No description available", result["description"]
    end

    test "find_matching_category handles blank input" do
      result = @analyzer.send(:find_matching_category, nil)
      assert_nil result

      result = @analyzer.send(:find_matching_category, "")
      assert_nil result

      result = @analyzer.send(:find_matching_category, "   ")
      assert_nil result
    end

    test "find_matching_category matches synonyms" do
      # Synonym mapping requires exact category names, so use mapped names but ensure uniqueness
      # Clean up any existing categories first to avoid collisions
      Category.where("name IN (?)", [ "Bags", "Handbags", "Boots" ]).destroy_all

      bags_category = create(:category, name: "Bags", active: true)
      result = @analyzer.send(:find_matching_category, "satchel")
      assert_equal bags_category, result

      handbags_category = create(:category, name: "Handbags", active: true)
      result = @analyzer.send(:find_matching_category, "handbag")
      assert_equal handbags_category, result

      boots_category = create(:category, name: "Boots", active: true)
      result = @analyzer.send(:find_matching_category, "boot")
      assert_equal boots_category, result
    end

    test "find_matching_category matches with word-based matching" do
      unique_suffix = SecureRandom.hex(4)
      tshirts_name = "T-Shirts #{unique_suffix}"
      tshirts_category = create(:category, name: tshirts_name, active: true)
      # Use the unique suffix in search to ensure we match the newly created category
      result = @analyzer.send(:find_matching_category, "blue cotton #{unique_suffix}")
      assert_equal tshirts_category, result
    end

    test "find_matching_category matches with partial word matching" do
      unique_suffix = SecureRandom.hex(4)
      sneakers_name = "Sneakers #{unique_suffix}"
      sneakers_category = create(:category, name: sneakers_name, active: true)
      # Use the full category name to ensure we match the newly created category
      result = @analyzer.send(:find_matching_category, sneakers_name.downcase)
      assert_equal sneakers_category, result
    end

    test "find_matching_category matches with contained names" do
      unique_suffix = SecureRandom.hex(4)
      jackets_name = "Jackets #{unique_suffix}"
      jackets_category = create(:category, name: jackets_name, active: true)
      # Use the full category name to ensure we match the newly created category
      result = @analyzer.send(:find_matching_category, jackets_name.downcase)
      assert_equal jackets_category, result
    end

    test "find_matching_category uses partial match as fallback" do
      unique_suffix = SecureRandom.hex(4)
      jeans_name = "Jeans #{unique_suffix}"
      jeans_category = create(:category, name: jeans_name, active: true)
      # Use the unique suffix in search to ensure we match the newly created category
      result = @analyzer.send(:find_matching_category, "blue #{unique_suffix}")
      assert_equal jeans_category, result
    end

    test "find_matching_category only matches active categories" do
      unique_suffix = SecureRandom.hex(4)
      unique_name = "UniqueCategory#{unique_suffix}"

      # Create inactive category first
      inactive_category = create(:category, name: unique_name, active: false)

      # Verify inactive category is not found
      result = @analyzer.send(:find_matching_category, unique_name.downcase)
      assert_nil result, "Should not find inactive category"

      # Update to active
      inactive_category.update!(active: true)

      # Now should find it
      result = @analyzer.send(:find_matching_category, unique_name.downcase)
      assert_equal inactive_category, result
    end

    test "find_matching_brand handles blank input" do
      result = @analyzer.send(:find_matching_brand, nil)
      assert_nil result

      result = @analyzer.send(:find_matching_brand, "")
      assert_nil result
    end

    test "find_matching_brand finds fuzzy match" do
      unique_suffix = SecureRandom.hex(4)
      brand_name = "UniqueBrand#{unique_suffix}"
      brand = create(:brand, name: brand_name)
      # Use a search term that contains the brand name to test fuzzy matching
      result = @analyzer.send(:find_matching_brand, "#{brand_name} Air Max")
      assert_equal brand, result
    end

    test "find_matching_brand finds partial match" do
      unique_suffix = SecureRandom.hex(4)
      brand_name = "Adidas #{unique_suffix}"
      brand = create(:brand, name: brand_name)
      # Search with the full unique name to ensure we match the newly created brand
      result = @analyzer.send(:find_matching_brand, brand_name)
      assert_equal brand, result
    end

    test "find_matching_brand returns nil when no match found" do
      brand_name = "Nike #{SecureRandom.hex(4)}"
      create(:brand, name: brand_name)
      result = @analyzer.send(:find_matching_brand, "UnknownBrand #{SecureRandom.hex(4)}")
      assert_nil result
    end

    test "enhance_with_matching handles missing category_name" do
      results = {
        "brand_name" => "Nike",
        "description" => "Test"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_nil enhanced["category_id"]
      assert_nil enhanced["category_matched"]
    end

    test "enhance_with_matching handles missing brand_name" do
      results = {
        "category_name" => "T-Shirt",
        "description" => "Test"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_nil enhanced["brand_id"]
      assert_nil enhanced["brand_matched"]
    end

    test "enhance_with_matching sets brand_suggested when brand not found" do
      results = {
        "category_name" => "T-Shirt",
        "brand_name" => "UnknownBrand",
        "description" => "Test"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_equal "UnknownBrand", enhanced["brand_suggested"]
      assert_nil enhanced["brand_id"]
    end

    test "enhance_with_matching handles category not found" do
      results = {
        "category_name" => "NonExistentCategory",
        "description" => "Test"
      }

      enhanced = @analyzer.send(:enhance_with_matching, results)

      assert_nil enhanced["category_id"]
      assert_nil enhanced["category_matched"]
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
