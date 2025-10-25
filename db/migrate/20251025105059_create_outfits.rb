class CreateOutfits < ActiveRecord::Migration[8.1]
  def change
    create_table :outfits do |t|
      t.references :user, null: false, foreign_key: true
      t.string :name
      t.string :occasion
      t.string :season
      t.boolean :is_favorite
      t.boolean :is_public

      t.timestamps
    end
  end
end
