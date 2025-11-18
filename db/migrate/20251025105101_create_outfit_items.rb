class CreateOutfitItems < ActiveRecord::Migration[8.1]
  def change
    create_table :outfit_items do |t|
      t.references :outfit, null: false, foreign_key: true
      # Use inventory_item from start (consolidated from add_inventory_item_id migration)
      t.references :inventory_item, null: false, foreign_key: true
      t.integer :position
      
      # Consolidated from add_missing_attributes migration
      t.text :notes
      
      # Consolidated from enhance_outfit_management_system
      t.integer :worn_count, default: 0
      t.datetime :last_worn_at
      t.text :styling_notes

      t.timestamps
    end
    
    # Unique index consolidated from enhance_outfit_management_system
    add_index :outfit_items, [ :outfit_id, :inventory_item_id ], unique: true, name: "index_outfit_items_unique"
  end
end
