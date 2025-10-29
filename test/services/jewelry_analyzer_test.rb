require "test_helper"

class JewelryAnalyzerTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @item = create(:inventory_item, item_type: "jewelry", user: @user, category: @category)
    @analyzer = Services::JewelryAnalyzer.new(@item)
  end

  test "jewelry_analysis_prompt includes item details" do
    prompt = @analyzer.send(:jewelry_analysis_prompt)
    assert_includes prompt, "jewelry"
  end

  test "parse_analysis_response extracts JSON" do
    json_content = '{"item_type":"jewelry","metal_type":"gold","confidence":0.9}'
    result = @analyzer.send(:parse_analysis_response, json_content)
    assert_equal "jewelry", result["item_type"]
    assert_equal "gold", result["metal_type"]
  end

  test "analysis_type returns visual_analysis" do
    assert_equal "visual_analysis", @analyzer.send(:analysis_type)
  end
end
