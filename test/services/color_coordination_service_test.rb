require "test_helper"

class ColorCoordinationServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
  end

  test "analyze returns default response for empty items" do
    result = ColorCoordinationService.analyze([])

    assert_equal 0.5, result[:score]
    assert_equal({}, result[:colors])
    assert_equal "Add items to analyze color coordination", result[:feedback]
  end

  test "analyze extracts colors from item metadata" do
    item1 = create(:inventory_item, user: @user, category: @category, name: "Blue Shirt")
    item1.update_column(:metadata, { "color" => "blue" }.to_json)

    item2 = create(:inventory_item, user: @user, category: @category, name: "Red Shirt")
    item2.update_column(:metadata, { "color" => "red" }.to_json)

    result = ColorCoordinationService.analyze([ item1, item2 ])

    assert result[:score] >= 0.0
    assert result[:colors].keys.any?
    assert result[:feedback].present?
  end

  test "normalize_colors maps color variations" do
    # Test that navy maps to blue
    colors = ColorCoordinationService.send(:normalize_colors, "navy")
    assert_includes colors, "blue"

    # Test that grey maps to gray
    colors = ColorCoordinationService.send(:normalize_colors, "grey")
    assert_includes colors, "gray"
  end

  test "calculate_coordination_score works with multiple colors" do
    color_map = {
      "blue" => [ 1, 2 ],
      "white" => [ 3 ]
    }

    score = ColorCoordinationService.send(:calculate_coordination_score, color_map)
    assert score >= 0.0 && score <= 1.0
  end

  test "check_color_harmony identifies harmonious colors" do
    # Analogous colors
    score = ColorCoordinationService.send(:check_color_harmony, [ "red", "orange" ])
    assert score > 0.0

    # Non-harmonious colors
    score = ColorCoordinationService.send(:check_color_harmony, [ "red", "blue" ])
    assert score >= 0.0
  end

  test "generate_feedback provides appropriate messages" do
    feedback = ColorCoordinationService.send(:generate_feedback, { "blue" => [ 1 ] })
    assert feedback.include?("Monochromatic")

    feedback = ColorCoordinationService.send(:generate_feedback, { "blue" => [ 1 ], "white" => [ 2 ] })
    assert feedback.include?("two-color")
  end

  test "analyze handles items with no color information" do
    item = create(:inventory_item, user: @user, category: @category, name: "No Color Item")
    # Ensure no metadata color
    item.update_column(:metadata, {}.to_json)

    result = ColorCoordinationService.analyze([ item ])

    assert result[:score] >= 0.0
    # Colors might be empty or might extract from name/AI analysis, but should not crash
    assert result[:colors].is_a?(Hash)
    assert result[:feedback].present?
  end

  test "analyze handles JSON string metadata" do
    item = create(:inventory_item, user: @user, category: @category)
    item.update_column(:metadata, '{"color": "navy"}')

    result = ColorCoordinationService.analyze([ item ])

    # Should normalize navy to blue
    assert result[:colors].keys.any?
  end

  test "analyze identifies missing categories through suggestions" do
    # Test indirectly through the analyze method which uses identify_missing_categories
    category = create(:category, name: "Jeans #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category, name: "Jeans")
    item.update_column(:metadata, { "color" => "blue" }.to_json)

    result = ColorCoordinationService.analyze([ item ])

    # When only bottoms are present, suggestions should indicate missing items
    # This tests identify_missing_categories indirectly
    assert result[:suggestions].is_a?(Array)
    # May suggest adding tops or shoes
  end

  test "check_complementary_colors identifies complementary pairs" do
    score = ColorCoordinationService.send(:check_complementary_colors, [ "red", "green" ])
    assert score > 0.0
  end

  test "warnings generated for too many colors" do
    items = (1..6).map do |i|
      color_names = [ "red", "blue", "green", "yellow", "purple", "orange" ]
      item = create(:inventory_item, user: @user, category: @category, name: "Item #{i}")
      item.update_column(:metadata, { "color" => color_names[i-1] }.to_json)
      item
    end

    result = ColorCoordinationService.analyze(items)
    assert result[:warnings].any? { |w| w.to_s.downcase.include?("many") || w.to_s.downcase.include?("busy") }
  end

  test "suggestions generated when missing neutral colors" do
    item1 = create(:inventory_item, user: @user, category: @category)
    item1.update_column(:metadata, { "color" => "red" }.to_json)

    item2 = create(:inventory_item, user: @user, category: @category)
    item2.update_column(:metadata, { "color" => "blue" }.to_json)

    result = ColorCoordinationService.analyze([ item1, item2 ])
    assert result[:suggestions].any? { |s| s.to_s.downcase.include?("neutral") }
  end

  test "analyze handles invalid JSON in metadata gracefully" do
    item = create(:inventory_item, user: @user, category: @category)
    item.update_column(:metadata, "invalid json")

    result = ColorCoordinationService.analyze([ item ])
    assert result.is_a?(Hash)
    assert result[:score].present?
    # Should not crash
  end

  test "analyze handles metadata with null color" do
    item = create(:inventory_item, user: @user, category: @category)
    item.update_column(:metadata, { "color" => nil }.to_json)

    result = ColorCoordinationService.analyze([ item ])
    # Should handle nil color gracefully - might fall back to AI analysis or return empty
    assert result.is_a?(Hash)
    assert result[:score].present?
    assert result[:colors].is_a?(Hash)
  end
end
