require "test_helper"

class ShoesAnalyzerTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @item = create(:inventory_item, :shoes, user: @user, category: @category, name: "Running Shoes")
    @analyzer = Services::ShoesAnalyzer.new(@item)
  end

  test "shoes_analysis_prompt includes item details" do
    prompt = @analyzer.send(:shoes_analysis_prompt)
    assert_includes prompt, "shoes"
    assert_includes prompt, "Running Shoes"
  end

  test "parse_analysis_response extracts JSON from response" do
    json_content = '{"item_type":"shoes","colors":["black"],"style":"athletic","confidence":0.85}'
    result = @analyzer.send(:parse_analysis_response, json_content)
    assert_equal "shoes", result["item_type"]
    assert_equal [ "black" ], result["colors"]
    assert_equal "athletic", result["style"]
  end

  test "parse_analysis_response uses fallback when no JSON found" do
    text = "Plain text without JSON"
    result = @analyzer.send(:parse_analysis_response, text)
    assert_equal "shoes", result["item_type"]
    assert_equal [ "unknown" ], result["colors"]
    assert_equal 0.5, result["confidence"]
  end

  test "analysis_type returns visual_analysis" do
    assert_equal "visual_analysis", @analyzer.send(:analysis_type)
  end

  test "parse_analysis_response handles JSON::ParserError" do
    invalid_json = '{"invalid": json}'
    Rails.logger.stubs(:error)

    result = @analyzer.send(:parse_analysis_response, invalid_json)

    assert_equal "shoes", result["item_type"]
    assert_equal [ "unknown" ], result["colors"]
    assert_equal "unable to analyze", result["style"]
    assert_equal 0.0, result["confidence"]
  end

  test "parse_analysis_response extracts JSON from multiline content" do
    content = "Here is some text before\n{\"item_type\":\"shoes\",\"colors\":[\"black\"],\"style\":\"athletic\",\"confidence\":0.9}\nAnd text after"
    result = @analyzer.send(:parse_analysis_response, content)

    assert_equal "shoes", result["item_type"]
    assert_equal [ "black" ], result["colors"]
    assert_equal "athletic", result["style"]
    assert_equal 0.9, result["confidence"]
  end

  test "shoes_analysis_prompt includes item name" do
    @item.update(name: "Nike Running Shoes")
    prompt = @analyzer.send(:shoes_analysis_prompt)

    assert_includes prompt, "Nike Running Shoes"
  end

  test "shoes_analysis_prompt handles nil category" do
    @item.update(category: nil)
    prompt = @analyzer.send(:shoes_analysis_prompt)

    assert_includes prompt, "Not specified"
  end

  test "shoes_analysis_prompt handles nil brand" do
    @item.update(brand: nil)
    prompt = @analyzer.send(:shoes_analysis_prompt)

    assert_includes prompt, "Not specified"
  end

  test "perform_analysis creates user message and calls chat.ask" do
    chat = create(:chat, user: @user)
    mock_assistant_message = mock
    mock_assistant_message.stubs(:content).returns('{"item_type":"shoes","confidence":0.8}')

    message_created = false
    chat.stubs(:ask).returns(mock_assistant_message)
    chat.messages.expects(:create!).with { |args| message_created = true; args[:role] == "user" }.returns(mock)

    result = @analyzer.perform_analysis(chat)

    assert message_created, "User message should be created"
    assert_equal "shoes", result["item_type"]
    assert_equal 0.8, result["confidence"]
  end

  test "shoes_analysis_prompt includes all required fields" do
    prompt = @analyzer.send(:shoes_analysis_prompt)

    assert_includes prompt, "Item type"
    assert_includes prompt, "Category"
    assert_includes prompt, "Brand"
    assert_includes prompt, "Colors"
    assert_includes prompt, "Style"
    assert_includes prompt, "Material"
    assert_includes prompt, "Season"
    assert_includes prompt, "Occasion"
    assert_includes prompt, "Confidence"
  end
end
