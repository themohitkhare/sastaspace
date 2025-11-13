require "test_helper"

class ClothingAnalyzerTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Blue T-Shirt")
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
    @chat = Chat.create!(user: @user, model: @model)
    @analyzer = Services::ClothingAnalyzer.new(@item)
  end

  test "clothing_analysis_prompt includes item details" do
    prompt = @analyzer.send(:clothing_analysis_prompt)
    assert_includes prompt, "clothing"
    assert_includes prompt, "Blue T-Shirt"
  end

  test "extract_colors_from_text finds colors in text" do
    text = "This is a red and blue shirt with green accents"
    colors = @analyzer.send(:extract_colors_from_text, text)
    assert_includes colors, "red"
    assert_includes colors, "blue"
    assert_includes colors, "green"
  end

  test "extract_colors_from_text returns unknown when no colors found" do
    text = "This is a description without any color words"
    colors = @analyzer.send(:extract_colors_from_text, text)
    assert_equal [ "unknown" ], colors
  end

  test "parse_analysis_response extracts JSON from response" do
    json_content = '{"item_type":"clothing","colors":["blue"],"style":"casual","confidence":0.9}'
    result = @analyzer.send(:parse_analysis_response, "Some text #{json_content} more text")
    assert_equal "clothing", result["item_type"]
    assert_equal [ "blue" ], result["colors"]
    assert_equal 0.9, result["confidence"]
  end

  test "parse_analysis_response uses fallback when no JSON found" do
    text = "This is just plain text without any JSON"
    result = @analyzer.send(:parse_analysis_response, text)
    assert_equal "clothing", result["item_type"]
    assert_equal [ "unknown" ], result["colors"]
    assert_equal 0.5, result["confidence"]
  end

  test "parse_analysis_response handles JSON parsing errors" do
    invalid_json = '{"item_type":"clothing","colors":}'
    result = @analyzer.send(:parse_analysis_response, invalid_json)
    assert_equal "clothing", result["item_type"]
    assert_equal [ "unknown" ], result["colors"]
    assert_equal 0.0, result["confidence"]
  end

  test "analysis_type returns visual_analysis" do
    assert_equal "visual_analysis", @analyzer.send(:analysis_type)
  end

  test "parse_analysis_response handles JSON::ParserError with logging" do
    invalid_json = '{"invalid": json}'
    log_messages = []
    Rails.logger.stubs(:error).with { |msg| log_messages << msg; true }

    result = @analyzer.send(:parse_analysis_response, invalid_json)

    assert_equal "clothing", result["item_type"]
    assert_equal [ "unknown" ], result["colors"]
    assert_equal "unable to analyze", result["style"]
    assert_equal 0.0, result["confidence"]
    error_log = log_messages.find { |msg| msg.include?("Failed to parse analysis response") }
    assert error_log.present?, "Should log parsing error"
  end

  test "parse_analysis_response uses inventory_item.item_type in fallback" do
    @item.update(item_type: "tops")
    text = "Plain text without JSON"
    result = @analyzer.send(:parse_analysis_response, text)

    assert_equal "tops", result["item_type"]
  end

  test "extract_colors_from_text finds multiple colors" do
    text = "A red, blue, and green shirt with yellow accents"
    colors = @analyzer.send(:extract_colors_from_text, text)

    assert_includes colors, "red"
    assert_includes colors, "blue"
    assert_includes colors, "green"
    assert_includes colors, "yellow"
  end

  test "extract_colors_from_text is case insensitive" do
    text = "This is a RED and Blue shirt"
    colors = @analyzer.send(:extract_colors_from_text, text)

    assert_includes colors, "red"
    assert_includes colors, "blue"
  end

  test "extract_colors_from_text handles gray and grey" do
    text = "A gray shirt with grey accents"
    colors = @analyzer.send(:extract_colors_from_text, text)

    assert_includes colors, "gray"
    assert_includes colors, "grey"
  end

  test "extract_colors_from_text handles all color words" do
    color_words = [ "red", "blue", "green", "yellow", "black", "white", "gray", "brown", "purple", "pink", "orange", "navy", "beige", "tan" ]
    text = color_words.join(" and ")
    colors = @analyzer.send(:extract_colors_from_text, text)

    color_words.each do |color|
      assert_includes colors, color, "Should find #{color}"
    end
  end

  test "clothing_analysis_prompt includes item name" do
    @item.update(name: "Denim Jacket")
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Denim Jacket"
  end

  test "clothing_analysis_prompt handles nil category" do
    @item.update(category: nil)
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Not specified"
  end

  test "clothing_analysis_prompt handles nil brand" do
    @item.update(brand: nil)
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Not specified"
  end

  test "clothing_analysis_prompt includes category name when present" do
    category = create(:category, name: "Tops")
    @item.update(category: category)
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Tops"
  end

  test "clothing_analysis_prompt includes brand name when present" do
    brand = create(:brand, name: "Nike")
    @item.update(brand: brand)
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Nike"
  end

  test "perform_analysis creates user message and calls chat.ask" do
    mock_assistant_message = mock
    mock_assistant_message.stubs(:content).returns('{"item_type":"clothing","colors":["blue"],"confidence":0.8}')

    message_created = false
    @chat.stubs(:ask).returns(mock_assistant_message)
    @chat.messages.expects(:create!).with { |args| message_created = true; args[:role] == "user" }.returns(mock)

    result = @analyzer.perform_analysis(@chat)

    assert message_created, "User message should be created"
    assert_equal "clothing", result["item_type"]
    assert_equal [ "blue" ], result["colors"]
    assert_equal 0.8, result["confidence"]
  end

  test "clothing_analysis_prompt includes all required fields" do
    prompt = @analyzer.send(:clothing_analysis_prompt)

    assert_includes prompt, "Item type"
    assert_includes prompt, "Category"
    assert_includes prompt, "Brand"
    assert_includes prompt, "Name"
    assert_includes prompt, "Colors"
    assert_includes prompt, "Style"
    assert_includes prompt, "Material"
    assert_includes prompt, "Season"
    assert_includes prompt, "Occasion"
    assert_includes prompt, "Confidence"
  end

  test "parse_analysis_response extracts JSON from multiline content" do
    content = "Here is some text before\n{\"item_type\":\"clothing\",\"colors\":[\"red\",\"blue\"],\"style\":\"casual\",\"confidence\":0.9}\nAnd text after"
    result = @analyzer.send(:parse_analysis_response, content)

    assert_equal "clothing", result["item_type"]
    assert_equal [ "red", "blue" ], result["colors"]
    assert_equal "casual", result["style"]
    assert_equal 0.9, result["confidence"]
  end

  test "parse_analysis_response fallback uses extract_colors_from_text" do
    text = "This is a red and blue shirt description"
    result = @analyzer.send(:parse_analysis_response, text)

    assert_equal "clothing", result["item_type"]
    assert_includes result["colors"], "red"
    assert_includes result["colors"], "blue"
    assert_equal "uncertain", result["style"]
    assert_equal 0.5, result["confidence"]
  end
end
