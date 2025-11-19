# Background job for backfilling stock photo extraction
# This processes items in batches asynchronously, which is better for large datasets
class BackfillStockPhotoExtractionJob < ApplicationJob
  queue_as :default

  def perform(user_id, item_ids)
    user = User.find(user_id)
    items = user.inventory_items
                .where(id: item_ids)
                .active
                .without_stock_photo_extraction
                .includes(:category, :subcategory, :brand, :primary_image_attachment)

    processed = 0
    errors = []

    items.find_each do |item|
      next unless item.primary_image.attached?

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

        service.queue_extraction
        processed += 1
      rescue StandardError => e
        errors << { item_id: item.id, error: e.message }
        Rails.logger.error "Backfill failed for item #{item.id}: #{e.message}"
      end
    end

    Rails.logger.info "Backfill completed: #{processed} items queued, #{errors.count} errors for user #{user_id}"
    { processed: processed, errors: errors }
  end
end
