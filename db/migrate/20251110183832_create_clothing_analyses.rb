class CreateClothingAnalyses < ActiveRecord::Migration[8.1]
  def change
    create_table :clothing_analyses do |t|
      t.references :user, null: false, foreign_key: true
      t.bigint :image_blob_id, null: false
      t.jsonb :parsed_data, default: {}
      t.integer :items_detected, default: 0
      t.decimal :confidence, precision: 3, scale: 2
      t.string :status, default: "completed", null: false

      t.timestamps
    end

    add_index :clothing_analyses, :image_blob_id
    add_index :clothing_analyses, :status
    add_index :clothing_analyses, :created_at
  end
end
