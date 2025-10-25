class AddMissingAttributesToOutfits < ActiveRecord::Migration[8.1]
  def change
    add_column :outfits, :description, :text
  end
end
