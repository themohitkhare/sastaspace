class AddMoreMissingAttributesToClothingItems < ActiveRecord::Migration[8.1]
  def change
    add_column :clothing_items, :analysis_status, :string
    add_column :clothing_items, :last_analyzed_at, :datetime
  end
end
