class AddHighConfidenceToAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    add_column :ai_analyses, :high_confidence, :boolean
  end
end
