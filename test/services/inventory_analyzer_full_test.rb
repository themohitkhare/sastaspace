require "test_helper"

class InventoryAnalyzerFullTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
    @chat = Chat.create!(user: @user, model: @model)
  end

  test "analyze creates or finds chat" do
    analyzer = Services::ClothingAnalyzer.new(@item)

    Chat.expects(:find_or_create_by!).returns(@chat)
    analyzer.stubs(:perform_analysis).returns({ "confidence" => 0.9 })
    EmbeddingService.stubs(:generate_for_item).returns(nil)

    analyzer.analyze
  end

  test "analyze saves analysis results" do
    analyzer = Services::ClothingAnalyzer.new(@item)
    results = { "confidence" => 0.85, "colors" => [ "blue" ] }

    analyzer.stubs(:create_or_find_chat).returns(@chat)
    analyzer.stubs(:perform_analysis).returns(results)
    EmbeddingService.stubs(:generate_for_item).returns(nil)

    assert_difference("AiAnalysis.count", 1) do
      analyzer.analyze
    end

    analysis = AiAnalysis.last
    assert_equal 0.85, analysis.confidence_score
    assert_equal @item, analysis.inventory_item
  end

  test "save_analysis uses default confidence when not provided" do
    analyzer = Services::ClothingAnalyzer.new(@item)
    results = { "colors" => [ "red" ] }

    analyzer.stubs(:create_or_find_chat).returns(@chat)
    analyzer.stubs(:perform_analysis).returns(results)
    EmbeddingService.stubs(:generate_for_item).returns(nil)

    analyzer.analyze

    analysis = AiAnalysis.last
    assert_equal 0.8, analysis.confidence_score
  end

  test "save_analysis sets high_confidence flag correctly" do
    analyzer = Services::ClothingAnalyzer.new(@item)
    high_conf_results = { "confidence" => 0.9 }

    analyzer.stubs(:create_or_find_chat).returns(@chat)
    analyzer.stubs(:perform_analysis).returns(high_conf_results)
    EmbeddingService.stubs(:generate_for_item).returns(nil)

    analyzer.analyze

    analysis = AiAnalysis.last
    assert_equal true, analysis.high_confidence
  end

  test "generate_embedding updates inventory_item when embedding is present" do
    analyzer = Services::ClothingAnalyzer.new(@item)
    embedding = [ 0.1 ] * 1536

    analyzer.stubs(:create_or_find_chat).returns(@chat)
    analyzer.stubs(:perform_analysis).returns({ "confidence" => 0.8 })
    EmbeddingService.stubs(:generate_for_item).returns(embedding)

    analyzer.analyze

    @item.reload
    assert_equal embedding, @item.embedding_vector
  end

  test "generate_embedding does not update when embedding is nil" do
    analyzer = Services::ClothingAnalyzer.new(@item)

    analyzer.stubs(:create_or_find_chat).returns(@chat)
    analyzer.stubs(:perform_analysis).returns({ "confidence" => 0.8 })
    EmbeddingService.stubs(:generate_for_item).returns(nil)

    original_vector = @item.embedding_vector
    analyzer.analyze

    @item.reload
    assert_equal original_vector, @item.embedding_vector
  end

  test "model creates Model record if it doesn't exist" do
    analyzer = Services::ClothingAnalyzer.new(@item, model_name: "custom-model")

    analyzer.send(:model)

    model = Model.find_by(model_id: "custom-model")
    assert_not_nil model
    assert_equal "custom-model", model.name
    assert_equal "openai", model.provider
  end

  test "model_provider returns openai" do
    analyzer = Services::InventoryAnalyzer.new(@item)
    assert_equal "openai", analyzer.send(:model_provider)
  end
end
