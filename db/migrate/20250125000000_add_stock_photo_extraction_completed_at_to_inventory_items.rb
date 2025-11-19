class AddStockPhotoExtractionCompletedAtToInventoryItems < ActiveRecord::Migration[8.1]
  def change
    add_column :inventory_items, :stock_photo_extraction_completed_at, :datetime, null: true
    add_index :inventory_items, :stock_photo_extraction_completed_at
  end
end
