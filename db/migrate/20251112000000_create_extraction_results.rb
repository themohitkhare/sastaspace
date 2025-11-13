class CreateExtractionResults < ActiveRecord::Migration[8.1]
  def change
    create_table :extraction_results do |t|
      t.references :clothing_analysis, null: false, foreign_key: true
      t.jsonb :item_data, default: {}
      t.bigint :extracted_image_blob_id
      t.decimal :extraction_quality, precision: 3, scale: 2
      t.string :status, default: "pending", null: false

      t.timestamps
    end

    add_index :extraction_results, :status
    add_index :extraction_results, :extracted_image_blob_id
    add_index :extraction_results, :created_at
  end
end
