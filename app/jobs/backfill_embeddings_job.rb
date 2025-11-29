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
          item.update_column(:embedding_vector, vector)
          count += 1
        end
      rescue StandardError => e
        Rails.logger.error "Failed to generate embedding for item #{item.id}: #{e.message}"
      end
    end

    Rails.logger.info "BackfillEmbeddingsJob completed. Processed #{count} items."

    # Re-queue if more items exist
    if InventoryItem.where(embedding_vector: nil).exists?
      BackfillEmbeddingsJob.set(wait: 1.minute).perform_later(batch_size: batch_size)
    end
  end
end
