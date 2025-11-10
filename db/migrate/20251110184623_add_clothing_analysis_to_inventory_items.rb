class AddClothingAnalysisToInventoryItems < ActiveRecord::Migration[8.1]
  def change
    add_reference :inventory_items, :clothing_analysis, null: true, foreign_key: true
  end
end
