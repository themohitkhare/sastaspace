class RemoveItemTypeAndDropClothingItems < ActiveRecord::Migration[7.1]
  def up
    if column_exists?(:inventory_items, :item_type)
      remove_column :inventory_items, :item_type, :string
    end

    # Clean up any legacy foreign keys/columns referencing clothing_items
    if table_exists?(:outfit_items)
      if foreign_key_exists?(:outfit_items, :clothing_items)
        remove_foreign_key :outfit_items, :clothing_items
      end
      if column_exists?(:outfit_items, :clothing_item_id)
        remove_column :outfit_items, :clothing_item_id
      end
    end

    drop_table :clothing_items if table_exists?(:clothing_items)
  end

  def down
    add_column :inventory_items, :item_type, :string unless column_exists?(:inventory_items, :item_type)

    # clothing_items table is legacy and won’t be recreated automatically
  end
end
