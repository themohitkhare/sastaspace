class CreateOutfitItems < ActiveRecord::Migration[8.1]
  def change
    create_table :outfit_items do |t|
      t.references :outfit, null: false, foreign_key: true
      t.references :clothing_item, null: false, foreign_key: true
      t.integer :position

      t.timestamps
    end
  end
end
