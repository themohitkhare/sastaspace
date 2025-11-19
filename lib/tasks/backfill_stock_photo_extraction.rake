# Rake task to backfill stock photo extraction for items that haven't had it completed yet
# Usage:
#   rails backfill:stock_photo_extraction[user_email]      # For specific user
#   rails backfill:stock_photo_extraction[user_email,100]  # With limit

namespace :backfill do
  desc "Trigger stock photo extraction for inventory items that haven't had it completed yet"
  desc "Options: [user_email, limit, use_background_job]"
  desc "  use_background_job: 'true' to process via background job (recommended for large datasets)"
  task :stock_photo_extraction, [ :user_email, :limit, :use_background_job ] => :environment do |_t, args|
    Rails.application.eager_load!

    user_email = args[:user_email]
    limit = (args[:limit] || 100).to_i
    use_background_job = args[:use_background_job] == "true"

    if user_email.blank?
      puts "Usage: rails backfill:stock_photo_extraction[user_email,limit,use_background_job]"
      puts "Example: rails backfill:stock_photo_extraction[user@example.com,50,true]"
      puts "\nOptions:"
      puts "  use_background_job: 'true' for async processing (recommended for >100 items)"
      exit 1
    end

    user = User.find_by(email: user_email)
    unless user
      puts "Error: User with email '#{user_email}' not found"
      exit 1
    end

    puts "=" * 60
    puts "Backfilling Stock Photo Extraction"
    puts "=" * 60
    puts "User: #{user.email} (ID: #{user.id})"
    puts "Limit: #{limit}"
    puts "Mode: #{use_background_job ? 'Background Job (async)' : 'Rake Task (sync)'}"
    puts "=" * 60

    # Find items without completed extraction
    items = user.inventory_items
                .active
                .without_stock_photo_extraction
                .limit(limit)
                .pluck(:id)

    puts "Found #{items.count} items without extraction"

    if use_background_job && items.any?
      # Process via background job (better for large datasets)
      # Split into batches of 50 for better performance
      items.each_slice(50) do |batch|
        BackfillStockPhotoExtractionJob.perform_later(user.id, batch)
      end
      puts "\n✓ Queued #{items.count} items for background processing"
      puts "  Split into #{(items.count / 50.0).ceil} batches"
      puts "  Check Sidekiq dashboard to monitor progress"
    elsif items.any?
      # Process synchronously in rake task (good for small datasets)
      items_with_data = user.inventory_items
                            .where(id: items)
                            .includes(:category, :subcategory, :brand, :primary_image_attachment)

      triggered = 0
      errors = []

      items_with_data.find_each do |item|
        unless item.primary_image.attached?
          puts "  ⚠ Skipping item #{item.id}: no primary image attached"
          errors << { item_id: item.id, error: "No primary image attached" }
          next
        end

        begin
          image_blob = item.primary_image.blob

          analysis_results = {
            name: item.name,
            description: item.description,
            category_name: item.category&.name,
            category_matched: item.category&.name,
            subcategory: item.subcategory&.name,
            material: item.material,
            style: item.style_notes,
            style_notes: item.style_notes,
            brand_matched: item.brand&.name,
            colors: [ item.color ].compact,
            extraction_prompt: item.extraction_prompt,
            gender_appropriate: true,
            confidence: 0.9
          }

          service = StockPhotoExtractionService.new(
            image_blob: image_blob,
            user: user,
            analysis_results: analysis_results,
            inventory_item_id: item.id
          )

          job_id = service.queue_extraction
          triggered += 1
          puts "  ✓ Queued extraction for item #{item.id} (job: #{job_id})"
        rescue StandardError => e
          error_msg = "Failed to trigger extraction for item #{item.id}: #{e.class} - #{e.message}"
          puts "  ✗ #{error_msg}"
          errors << { item_id: item.id, error: error_msg }
        end
      end

      puts "\n" + "=" * 60
      puts "Results:"
      puts "  Total found: #{items.count}"
      puts "  Triggered: #{triggered}"
      puts "  Errors: #{errors.count}"
      puts "=" * 60

      if errors.any?
        puts "\nErrors:"
        errors.each do |error|
          puts "  - Item #{error[:item_id]}: #{error[:error]}"
        end
      end
    else
      puts "No items found to process"
    end
  end

  desc "Trigger stock photo extraction for ALL users (use with caution)"
  task :stock_photo_extraction_all, [ :limit ] => :environment do |_t, args|
    # Eager load all application classes to ensure services are available
    # This is the recommended approach for rake tasks per Rails best practices
    Rails.application.eager_load!

    limit = (args[:limit] || 50).to_i

    puts "=" * 60
    puts "Backfilling Stock Photo Extraction for ALL Users"
    puts "=" * 60
    puts "Limit per user: #{limit}"
    puts "=" * 60

    total_triggered = 0
    total_errors = 0

    User.find_each do |user|
      items = user.inventory_items
                  .active
                  .without_stock_photo_extraction
                  .limit(limit)
                  .includes(:category, :subcategory, :brand, :primary_image_attachment)

      next if items.empty?

      puts "\nProcessing user: #{user.email} (ID: #{user.id}) - #{items.count} items"

      user_triggered = 0
      user_errors = 0

      items.each do |item|
        unless item.primary_image.attached?
          puts "  ⚠ Skipping item #{item.id}: no primary image attached"
          user_errors += 1
          next
        end

        begin
          image_blob = item.primary_image.blob

          analysis_results = {
            name: item.name,
            description: item.description,
            category_name: item.category&.name,
            category_matched: item.category&.name,
            subcategory: item.subcategory&.name,
            material: item.material,
            style: item.style_notes,
            style_notes: item.style_notes,
            brand_matched: item.brand&.name,
            colors: [ item.color ].compact,
            extraction_prompt: item.extraction_prompt,
            gender_appropriate: true,
            confidence: 0.9
          }

          service = StockPhotoExtractionService.new(
            image_blob: image_blob,
            user: user,
            analysis_results: analysis_results,
            inventory_item_id: item.id
          )

          job_id = service.queue_extraction
          user_triggered += 1
          puts "  ✓ Queued extraction for item #{item.id} (job: #{job_id})"
        rescue StandardError => e
          user_errors += 1
          puts "  ✗ Item #{item.id}: #{e.class} - #{e.message}"
        end
      end

      total_triggered += user_triggered
      total_errors += user_errors
      puts "  Triggered: #{user_triggered}, Errors: #{user_errors}"
    end

    puts "\n" + "=" * 60
    puts "Backfill complete for all users!"
    puts "  Total triggered: #{total_triggered}"
    puts "  Total errors: #{total_errors}"
    puts "=" * 60
  end
end
