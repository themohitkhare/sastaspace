class BackfillEmbeddingsJob < ApplicationJob
  queue_as :default

  def perform(batch_size: 100)
    Rails.logger.info "Starting BackfillEmbeddingsJob"

    items = InventoryItem.where(embedding_vector: nil).limit(batch_size)

    count = 0
    items.each do |item|
      begin
        vector = EmbeddingService.generate_for_item(item)
        if vector
          # Double-check dimensions before saving to prevent database errors
          if vector.length == EmbeddingService::EXPECTED_DIMENSIONS
            item.update_column(:embedding_vector, vector)
            count += 1
          else
            Rails.logger.error "Skipping item #{item.id}: embedding has #{vector.length} dimensions, expected #{EmbeddingService::EXPECTED_DIMENSIONS}"
          end
        else
          Rails.logger.warn "Failed to generate embedding for item #{item.id}: service returned nil"
        end
      rescue PG::DataException => e
        # Handle dimension mismatch errors from database
        if e.message.include?("expected") && e.message.include?("dimensions")
          Rails.logger.error "Dimension mismatch for item #{item.id}: #{e.message}"
          Rails.logger.error "This item may have a cached embedding with wrong dimensions. Clearing cache and skipping."
          Caching::EmbeddingCacheService.invalidate_item_embedding(item)
        else
          Rails.logger.error "Database error for item #{item.id}: #{e.message}"
        end
      rescue StandardError => e
        Rails.logger.error "Failed to generate embedding for item #{item.id}: #{e.message}"
        Rails.logger.error e.backtrace.first(3).join("\n") if e.backtrace
      end
    end

    Rails.logger.info "BackfillEmbeddingsJob completed. Processed #{count} items."

    # Re-queue if more items exist
    if InventoryItem.where(embedding_vector: nil).exists?
      BackfillEmbeddingsJob.set(wait: 1.minute).perform_later(batch_size: batch_size)
    end
  end
end
