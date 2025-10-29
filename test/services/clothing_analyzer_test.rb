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
end
