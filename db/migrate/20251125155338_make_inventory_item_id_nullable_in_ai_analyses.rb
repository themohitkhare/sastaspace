class MakeInventoryItemIdNullableInAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    change_column_null :ai_analyses, :inventory_item_id, true
  end
end
