module Services
  class AnalyzerFactory
    def self.create_analyzer(inventory_item, model_name: "gpt-4o-mini")
      case inventory_item.item_type
      when "clothing"
        ClothingAnalyzer.new(inventory_item, model_name: model_name)
      when "shoes"
        ShoesAnalyzer.new(inventory_item, model_name: model_name)
      when "accessories"
        AccessoriesAnalyzer.new(inventory_item, model_name: model_name)
      when "jewelry"
        JewelryAnalyzer.new(inventory_item, model_name: model_name)
      else
        Rails.logger.warn "Unknown item type #{inventory_item.item_type}, using default analyzer"
        ClothingAnalyzer.new(inventory_item, model_name: model_name)
      end
    end
  end
end

