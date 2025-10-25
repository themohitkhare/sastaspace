class CreateClothingItems < ActiveRecord::Migration[8.1]
  def change
    create_table :clothing_items do |t|
      t.references :user, null: false, foreign_key: true
      t.string :name
      t.string :category
      t.string :season
      t.string :occasion
      t.decimal :price
      t.string :image_hash

      t.timestamps
    end
  end
end
