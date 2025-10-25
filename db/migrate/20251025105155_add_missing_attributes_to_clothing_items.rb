class AddMissingAttributesToClothingItems < ActiveRecord::Migration[8.1]
  def change
    add_column :clothing_items, :brand, :string
    add_column :clothing_items, :color, :string
    add_column :clothing_items, :size, :string
    add_column :clothing_items, :purchase_date, :date
    add_column :clothing_items, :notes, :text
  end
end
