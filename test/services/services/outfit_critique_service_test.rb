require "test_helper"

class OutfitCritiqueServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @outfit = create(:outfit, user: @user, name: "Test Outfit", occasion: "casual")

    # Create items for outfit
    @item1 = create(:inventory_item, user: @user, name: "Blue Shirt", category: create(:category, name: "Shirts"))
    @item2 = create(:inventory_item, user: @user, name: "Jeans", category: create(:category, name: "Jeans"))

    @outfit.outfit_items.create!(inventory_item: @item1, position: 0)
    @outfit.outfit_items.create!(inventory_item: @item2, position: 1)

    # Stub Ollama client
    @mock_response = {
      "response" => {
        "score" => 85,
        "summary" => "Great casual outfit with good color coordination",
        "strengths" => [ "Color coordination works well", "Appropriate for casual occasion" ],
        "improvements" => [ "Consider adding accessories", "Try different shoe style" ],
        "tone" => "Encouraging but honest"
      }.to_json
    }
  end

  test "analyze returns error for outfit with no items" do
    empty_outfit = create(:outfit, user: @user)

    result = Services::OutfitCritiqueService.analyze(empty_outfit)

    assert result[:error].present?
    assert_match(/no items/i, result[:error])
  end

  test "analyze calls Ollama and returns structured critique" do
    # Stub the call_ollama method directly
    service = Services::OutfitCritiqueService.new(@outfit)
    parsed_data = JSON.parse(@mock_response["response"])
    service.expects(:call_ollama).returns({
      success: true,
      data: parsed_data
    })

    result = service.analyze

    assert result["score"].present? || result[:score].present?
    assert result["summary"].present? || result[:summary].present?
    assert (result["strengths"] || result[:strengths]).is_a?(Array)
    assert (result["improvements"] || result[:improvements]).is_a?(Array)
    score = result["score"] || result[:score]
    assert_equal 85, score
  end

  test "analyze stores result in ai_analyses" do
    service = Services::OutfitCritiqueService.new(@outfit)
    service.expects(:call_ollama).returns({
      success: true,
      data: JSON.parse(@mock_response["response"])
    })

    assert_difference "AiAnalysis.where(outfit: @outfit).count", 1 do
      service.analyze
    end

    analysis = AiAnalysis.where(outfit: @outfit).last
    assert_equal "outfit_critique", analysis.analysis_type
    assert analysis.analysis_data.present?
  end

  test "analyze returns cached result if recent analysis exists" do
    # Create a recent analysis
    cached_data = { "score" => 90, "summary" => "Cached critique" }
    AiAnalysis.create!(
      outfit: @outfit,
      user: @user,
      analysis_type: "outfit_critique",
      analysis_data: cached_data,
      confidence_score: 0.90,
      created_at: 1.hour.ago
    )

    # Should not call Ollama
    service = Services::OutfitCritiqueService.new(@outfit)
    service.expects(:call_ollama).never

    result = service.analyze

    assert_equal 90, result["score"] || result[:score]
    assert_equal "Cached critique", result["summary"] || result[:summary]
  end

  test "analyze calls Ollama if cached analysis is older than 1 day" do
    # Create old analysis
    AiAnalysis.create!(
      outfit: @outfit,
      user: @user,
      analysis_type: "outfit_critique",
      analysis_data: { "score" => 80 },
      confidence_score: 0.80,
      created_at: 2.days.ago
    )

    service = Services::OutfitCritiqueService.new(@outfit)
    parsed_data = JSON.parse(@mock_response["response"])
    service.expects(:call_ollama).returns({
      success: true,
      data: parsed_data
    })

    result = service.analyze
    score = result["score"] || result[:score]
    assert_equal 85, score # From new analysis, not cached
  end

  test "analyze handles Ollama errors gracefully" do
    service = Services::OutfitCritiqueService.new(@outfit)
    service.expects(:call_ollama).returns({
      success: false,
      error: "Empty response from AI"
    })

    result = service.analyze

    assert result[:error].present?
    assert_match(/unavailable|empty/i, result[:error])
  end

  test "analyze handles network errors" do
    service = Services::OutfitCritiqueService.new(@outfit)
    service.expects(:call_ollama).raises(StandardError, "Connection failed")

    result = service.analyze

    assert result.present?
    error_msg = result[:error] || result["error"]
    assert error_msg.present?
    assert_match(/unavailable/i, error_msg)
  end

  test "build_prompt includes outfit details" do
    service = Services::OutfitCritiqueService.new(@outfit)
    prompt = service.send(:build_prompt)

    assert_match(/Test Outfit/, prompt)
    assert_match(/casual/, prompt)
    assert_match(/Blue Shirt/, prompt)
    assert_match(/Jeans/, prompt)
    assert_match(/JSON format/, prompt)
  end

  test "format_result handles string JSON" do
    service = Services::OutfitCritiqueService.new(@outfit)
    result = service.send(:format_result, '{"score": 75, "summary": "Test"}')

    assert_equal 75, result["score"] || result[:score]
    assert_equal "Test", result["summary"] || result[:summary]
  end

  test "format_result handles hash data" do
    service = Services::OutfitCritiqueService.new(@outfit)
    data = { score: 80, summary: "Direct hash" }
    result = service.send(:format_result, data)

    assert_equal data, result
  end
end
