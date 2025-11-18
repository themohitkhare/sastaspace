class CreateExportJobs < ActiveRecord::Migration[8.1]
  def change
    create_table :export_jobs do |t|
      t.references :user, null: false, foreign_key: true
      t.string :status
      t.string :file_format
      
      # Consolidated from add_missing_attributes migration
      t.datetime :requested_at
      t.datetime :completed_at

      t.timestamps
    end
  end
end
