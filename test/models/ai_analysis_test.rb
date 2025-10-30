require "test_helper"

class AiAnalysisTest < ActiveSupport::TestCase
  setup do
    @user = FactoryBot.create(:user)
    @category = FactoryBot.create(:category, :clothing)
    @brand = FactoryBot.create(:brand)
    @inventory_item = FactoryBot.create(:inventory_item,
                                       user: @user,
                                       category: @category,
                                       brand: @brand,
                                       item_type: "clothing")
  end

  test "can create ai_analysis" do
    analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "blue" },
      confidence_score: 0.8
    )

    assert_not_nil analysis.id
    assert_equal @inventory_item, analysis.inventory_item
    assert_equal @user, analysis.user
    assert_equal "visual_analysis", analysis.analysis_type
  end

  test "belongs to inventory_item" do
    analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "red" },
      confidence_score: 0.9
    )

    assert_equal @inventory_item, analysis.inventory_item
    assert_equal analysis.inventory_item_id, @inventory_item.id
  end

  test "belongs to user" do
    analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "green" },
      confidence_score: 0.7
    )

    assert_equal @user, analysis.user
  end

  test "requires analysis_type" do
    analysis = AiAnalysis.new(
      inventory_item: @inventory_item,
      user: @user,
      analysis_data: { "color" => "blue" },
      confidence_score: 0.8
    )

    assert_not analysis.valid?
    assert_includes analysis.errors.full_messages, "Analysis type can't be blank"
  end

  test "requires confidence_score" do
    analysis = AiAnalysis.new(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "blue" }
    )

    assert_not analysis.valid?
    assert_includes analysis.errors.full_messages, "Confidence score can't be blank"
  end

  test "analysis_data_hash returns hash" do
    analysis_data = { "color" => "blue", "style" => "casual" }
    analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: analysis_data,
      confidence_score: 0.8
    )

    assert_equal analysis_data, analysis.analysis_data_hash
  end

  test "can access item type from analysis data" do
    analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "item_type" => "clothing", "colors" => [ "blue", "white" ] },
      confidence_score: 0.85
    )

    assert_equal "clothing", analysis.item_type
    assert_equal [ "blue", "white" ], analysis.colors
  end

  test "high_confidence scope works" do
    high_analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "blue" },
      confidence_score: 0.9,
      high_confidence: true
    )

    low_analysis = AiAnalysis.create!(
      inventory_item: @inventory_item,
      user: @user,
      analysis_type: "visual_analysis",
      analysis_data: { "color" => "red" },
      confidence_score: 0.6,
      high_confidence: false
    )

    high_confidence_analyses = AiAnalysis.high_confidence
    assert_includes high_confidence_analyses, high_analysis
    assert_not_includes high_confidence_analyses, low_analysis
  end
end
