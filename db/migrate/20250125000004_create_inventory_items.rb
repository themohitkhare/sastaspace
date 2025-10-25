class CreateInventoryItems < ActiveRecord::Migration[8.1]
  def change
    create_table :inventory_items do |t|
      t.references :user, null: false, foreign_key: true
      t.references :category, null: false, foreign_key: true  
      t.references :brand, null: true, foreign_key: true
      
      # Core fields
      t.string :name, null: false
      t.string :item_type, null: false
      t.text :description
      t.integer :status, default: 0
      
      # Flexible metadata as JSON
      t.json :metadata, default: {}
      
      # Vector embedding for AI similarity
      t.binary :embedding_vector
      
      # Inventory tracking
      t.decimal :purchase_price, precision: 8, scale: 2
      t.date :purchase_date
      t.integer :wear_count, default: 0
      t.datetime :last_worn_at
      
      t.timestamps
    end
    
    add_index :inventory_items, :item_type
    add_index :inventory_items, :status
    add_index :inventory_items, [:user_id, :category_id]
    add_index :inventory_items, :embedding_vector
    add_index :inventory_items, [:user_id, :item_type]
    add_index :inventory_items, :last_worn_at
  end
end
