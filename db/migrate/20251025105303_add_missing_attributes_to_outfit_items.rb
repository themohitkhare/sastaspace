class AddMissingAttributesToOutfitItems < ActiveRecord::Migration[8.1]
  def change
    add_column :outfit_items, :notes, :text
  end
end
