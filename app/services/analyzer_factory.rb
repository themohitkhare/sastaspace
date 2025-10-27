module Services
  class AnalyzerFactory
    def self.create_analyzer(inventory_item, model_name: "gpt-4o-mini")
      case inventory_item.item_type
      when "clothing"
        Services::ClothingAnalyzer.new(inventory_item, model_name: model_name)
      when "shoes"
        Services::ShoesAnalyzer.new(inventory_item, model_name: model_name)
      when "accessories"
        Services::AccessoriesAnalyzer.new(inventory_item, model_name: model_name)
      when "jewelry"
        Services::JewelryAnalyzer.new(inventory_item, model_name: model_name)
      else
        Rails.logger.warn "Unknown item type #{inventory_item.item_type}, using default analyzer"
        Services::ClothingAnalyzer.new(inventory_item, model_name: model_name)
      end
    end
  end
end
