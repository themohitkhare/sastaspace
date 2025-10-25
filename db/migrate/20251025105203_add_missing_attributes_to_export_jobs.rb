class AddMissingAttributesToExportJobs < ActiveRecord::Migration[8.1]
  def change
    add_column :export_jobs, :requested_at, :datetime
    add_column :export_jobs, :completed_at, :datetime
  end
end
