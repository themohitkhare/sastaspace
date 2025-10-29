require "test_helper"

class AnalyzerFactoryTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
  end

  test "create_analyzer returns ClothingAnalyzer for clothing items" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    analyzer = Services::AnalyzerFactory.create_analyzer(item)
    assert_instance_of Services::ClothingAnalyzer, analyzer
  end

  test "create_analyzer returns ShoesAnalyzer for shoes items" do
    item = create(:inventory_item, :shoes, user: @user, category: @category)
    analyzer = Services::AnalyzerFactory.create_analyzer(item)
    assert_instance_of Services::ShoesAnalyzer, analyzer
  end

  test "create_analyzer returns AccessoriesAnalyzer for accessories items" do
    item = create(:inventory_item, item_type: "accessories", user: @user, category: @category)
    analyzer = Services::AnalyzerFactory.create_analyzer(item)
    assert_instance_of Services::AccessoriesAnalyzer, analyzer
  end

  test "create_analyzer returns JewelryAnalyzer for jewelry items" do
    item = create(:inventory_item, item_type: "jewelry", user: @user, category: @category)
    analyzer = Services::AnalyzerFactory.create_analyzer(item)
    assert_instance_of Services::JewelryAnalyzer, analyzer
  end

  test "create_analyzer defaults to ClothingAnalyzer for unknown item types" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    item.stubs(:item_type).returns("unknown_type")
    Rails.logger.expects(:warn).with(regexp_matches(/Unknown item type/))
    analyzer = Services::AnalyzerFactory.create_analyzer(item)
    assert_instance_of Services::ClothingAnalyzer, analyzer
  end

  test "create_analyzer accepts custom model_name" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    analyzer = Services::AnalyzerFactory.create_analyzer(item, model_name: "custom-model")
    assert_equal "custom-model", analyzer.model_name
  end
end
