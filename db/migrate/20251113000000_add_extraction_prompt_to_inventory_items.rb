class AddExtractionPromptToInventoryItems < ActiveRecord::Migration[8.1]
  def change
    add_column :inventory_items, :extraction_prompt, :text
  end
end
