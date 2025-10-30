require "test_helper"

class EmbeddingServiceFullTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  test "build_item_description includes all relevant fields" do
    @item.brand = create(:brand)
    description = EmbeddingService.send(:build_item_description, @item)

    assert_includes description, @item.name
    assert_includes description, @item.item_type
    assert_includes description, @category.name
    assert_includes description, @item.brand.name
  end

  test "build_item_description handles missing optional fields" do
    @item.brand = nil
    description = EmbeddingService.send(:build_item_description, @item)

    assert_includes description, @item.name
    assert_not_includes description, "nil"
  end

  test "build_item_description includes analysis data when available" do
    analysis = create(:ai_analysis, inventory_item: @item, user: @user)
    analysis.analysis_data = {
      "style" => "casual",
      "material" => "cotton",
      "colors" => [ "blue", "white" ]
    }
    analysis.save!

    description = EmbeddingService.send(:build_item_description, @item)
    assert_includes description, "casual"
    assert_includes description, "cotton"
    assert_includes description, "blue"
  end
end
