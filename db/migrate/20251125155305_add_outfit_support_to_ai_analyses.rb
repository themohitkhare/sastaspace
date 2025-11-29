class AddOutfitSupportToAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    add_column :ai_analyses, :outfit_id, :integer
    add_index :ai_analyses, :outfit_id
  end
end
