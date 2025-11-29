namespace :backfill do
  desc "Generate embeddings for items that miss them (DEPRECATED: Use Maintenance Tasks UI at /maintenance_tasks)"
  task embeddings: :environment do
    puts "⚠️  DEPRECATED: This rake task is deprecated."
    puts "Please use the Maintenance Tasks UI at /maintenance_tasks"
    puts "Task name: Maintenance::BackfillEmbeddingsTask"
    puts ""
    puts "If you need to run it programmatically, use:"
    puts "  Maintenance::BackfillEmbeddingsTask.new.run"
  end
end
