class AddMoreMissingAttributesToOutfits < ActiveRecord::Migration[8.1]
  def change
    add_column :outfits, :weather_condition, :string
    add_column :outfits, :temperature_range, :string
  end
end
