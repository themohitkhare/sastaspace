class AddUserIdToAiAnalyses < ActiveRecord::Migration[8.1]
  def change
    add_reference :ai_analyses, :user, null: false, foreign_key: true
  end
end
