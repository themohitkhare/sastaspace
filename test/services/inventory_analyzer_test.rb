require "test_helper"

class InventoryAnalyzerTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  test "raises NotImplementedError for perform_analysis" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
    chat = Chat.create!(user: @user, model: model)

    assert_raises(NotImplementedError) do
      analyzer.send(:perform_analysis, chat)
    end
  end

  test "initializes with inventory_item and model_name" do
    analyzer = Services::InventoryAnalyzer.new(@item, model_name: "custom-model")
    assert_equal @item, analyzer.inventory_item
    assert_equal "custom-model", analyzer.model_name
  end

  test "uses default model_name when not provided" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    assert_equal "gpt-4o-mini", analyzer.model_name
  end

  test "analysis_prompt returns default prompt" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    prompt = analyzer.send(:analysis_prompt)
    assert_includes prompt, "clothing"
  end

  test "analysis_type returns visual_analysis" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    assert_equal "visual_analysis", analyzer.send(:analysis_type)
  end

  test "calculate_processing_time returns milliseconds" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    start_time = 1.second.ago
    duration = analyzer.send(:calculate_processing_time, start_time)
    assert duration.is_a?(Integer)
    assert duration >= 1000 # At least 1 second in milliseconds
  end
end
