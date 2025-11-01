class AddInventoryItemIdToOutfitItems < ActiveRecord::Migration[8.1]
  def up
    unless column_exists?(:outfit_items, :inventory_item_id)
      add_column :outfit_items, :inventory_item_id, :integer, null: false
      add_foreign_key :outfit_items, :inventory_items
      add_index :outfit_items, :inventory_item_id unless index_exists?(:outfit_items, :inventory_item_id)
    end
  end

  def down
    if column_exists?(:outfit_items, :inventory_item_id)
      remove_foreign_key :outfit_items, :inventory_items
      remove_index :outfit_items, :inventory_item_id if index_exists?(:outfit_items, :inventory_item_id)
      remove_column :outfit_items, :inventory_item_id
    end
  end
end
