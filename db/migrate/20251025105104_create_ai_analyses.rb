class CreateAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    create_table :ai_analyses do |t|
      # Use inventory_item from start (consolidated from fix_ai_analyses migration)
      t.references :inventory_item, null: false, foreign_key: true
      # Consolidated from add_user_id migration
      t.references :user, null: false, foreign_key: true

      t.string :analysis_type
      t.text :response
      t.decimal :confidence_score
      t.string :model_used
      t.integer :processing_time_ms

      # Consolidated from add_missing_attributes migration
      t.text :prompt_used
      t.string :image_hash

      # Consolidated from add_high_confidence migration
      t.boolean :high_confidence

      # Consolidated from fix_ai_analyses migration
      t.jsonb :analysis_data, default: {}

      t.timestamps
    end

    add_index :ai_analyses, :inventory_item_id
    add_index :ai_analyses, :user_id
  end
end
