class CreateInventoryTags < ActiveRecord::Migration[8.1]
  def change
    create_table :inventory_tags do |t|
      t.references :inventory_item, null: false, foreign_key: true
      t.references :tag, null: false, foreign_key: true

      t.timestamps
    end

    add_index :inventory_tags, [ :inventory_item_id, :tag_id ], unique: true
  end
end
