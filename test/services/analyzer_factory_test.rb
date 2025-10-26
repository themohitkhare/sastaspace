require "test_helper"

class Services::AnalyzerFactoryTest < ActiveSupport::TestCase
  setup do
    @user = FactoryBot.create(:user)
    @category = FactoryBot.create(:category, name: "Test Category")
  end

  test "creates clothing analyzer for clothing items" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "clothing")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item)
    
    assert_instance_of Services::ClothingAnalyzer, analyzer
  end

  test "creates shoes analyzer for shoes items" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "shoes")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item)
    
    assert_instance_of Services::ShoesAnalyzer, analyzer
  end

  test "creates accessories analyzer for accessories items" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "accessories")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item)
    
    assert_instance_of Services::AccessoriesAnalyzer, analyzer
  end

  test "creates jewelry analyzer for jewelry items" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "jewelry")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item)
    
    assert_instance_of Services::JewelryAnalyzer, analyzer
  end

  test "defaults to clothing analyzer for unknown types" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "unknown")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item)
    
    assert_instance_of Services::ClothingAnalyzer, analyzer
  end

  test "accepts model_name parameter" do
    inventory_item = FactoryBot.create(:inventory_item,
                                        user: @user,
                                        category: @category,
                                        item_type: "clothing")
    
    analyzer = Services::AnalyzerFactory.create_analyzer(inventory_item, model_name: "gpt-4")
    
    assert_equal "gpt-4", analyzer.model_name
  end
end

