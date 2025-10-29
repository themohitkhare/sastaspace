require "test_helper"

class AccessoriesAnalyzerTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @item = create(:inventory_item, item_type: "accessories", user: @user, category: @category)
    @analyzer = Services::AccessoriesAnalyzer.new(@item)
  end

  test "accessories_analysis_prompt includes item details" do
    prompt = @analyzer.send(:accessories_analysis_prompt)
    assert_includes prompt, "accessories"
  end

  test "parse_analysis_response extracts JSON" do
    json_content = '{"item_type":"accessories","colors":["brown"],"confidence":0.8}'
    result = @analyzer.send(:parse_analysis_response, json_content)
    assert_equal "accessories", result["item_type"]
  end

  test "analysis_type returns visual_analysis" do
    assert_equal "visual_analysis", @analyzer.send(:analysis_type)
  end
end
