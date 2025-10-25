class CreateAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    create_table :ai_analyses do |t|
      t.references :clothing_item, null: false, foreign_key: true
      t.string :analysis_type
      t.text :response
      t.decimal :confidence_score
      t.string :model_used
      t.integer :processing_time_ms

      t.timestamps
    end
  end
end
