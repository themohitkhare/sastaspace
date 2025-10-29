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
end
