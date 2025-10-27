class FixAiAnalysesForInventoryItems < ActiveRecord::Migration[8.1]
  def up
    # Add analysis_data column to store structured JSON data
    add_column :ai_analyses, :analysis_data, :jsonb, default: {}

    # Remove old foreign key constraint to clothing_items
    remove_foreign_key :ai_analyses, :clothing_items if foreign_key_exists?(:ai_analyses, :clothing_items)

    # Remove index on old column
    remove_index :ai_analyses, :clothing_item_id if index_exists?(:ai_analyses, :clothing_item_id)

    # Rename column from clothing_item_id to inventory_item_id
    rename_column :ai_analyses, :clothing_item_id, :inventory_item_id

    # Add new index and foreign key constraint to inventory_items
    add_index :ai_analyses, :inventory_item_id
    add_foreign_key :ai_analyses, :inventory_items
  end

  def down
    # Reverse the migration
    remove_foreign_key :ai_analyses, :inventory_items if foreign_key_exists?(:ai_analyses, :inventory_items)
    remove_index :ai_analyses, :inventory_item_id if index_exists?(:ai_analyses, :inventory_item_id)
    rename_column :ai_analyses, :inventory_item_id, :clothing_item_id
    add_index :ai_analyses, :clothing_item_id
    add_foreign_key :ai_analyses, :clothing_items
    remove_column :ai_analyses, :analysis_data
  end
end
