class AddSubcategoryToInventoryItems < ActiveRecord::Migration[7.1]
  def change
    add_reference :inventory_items, :subcategory, foreign_key: { to_table: :categories }, index: true, null: true
  end
end
