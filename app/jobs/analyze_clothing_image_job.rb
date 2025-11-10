class AnalyzeClothingImageJob < ApplicationJob
  include Monitorable

  queue_as :default

  def perform(inventory_item_id, model_name: "gpt-4o-mini")
    @inventory_item = InventoryItem.find(inventory_item_id)

    Rails.logger.info "Starting RubyLLM-based analysis for inventory item #{inventory_item_id}"

    # Use the analyzer factory to get the right analyzer
    analyzer = Services::AnalyzerFactory.create_analyzer(@inventory_item, model_name: model_name)

    # Perform analysis using RubyLLM
    analyzer.analyze

    Rails.logger.info "Analysis completed for inventory item #{inventory_item_id}"
  rescue StandardError => e
    Rails.logger.error "Failed to analyze inventory item #{inventory_item_id}: #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    raise e
  end
end
