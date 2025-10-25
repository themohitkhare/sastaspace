class AddMissingAttributesToAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    add_column :ai_analyses, :prompt_used, :text
    add_column :ai_analyses, :image_hash, :string
  end
end
