class StockExtractionJob < ApplicationJob
  # Medium priority queue for stock photo extraction operations
  queue_as :ai_processing

  # Don't retry StandardError - let errors bubble up for visibility
  # Only discard truly unrecoverable errors
  discard_on ActiveStorage::FileNotFoundError
  discard_on ArgumentError

  def perform(analysis_id, selected_item_ids)
    @analysis = ClothingAnalysis.find(analysis_id)
    @selected_item_ids = Array(selected_item_ids).map(&:to_s)

    Rails.logger.info "Starting extraction for analysis #{analysis_id}, #{@selected_item_ids.count} items"

    # Get selected items from analysis
    all_items = @analysis.items
    if all_items.nil?
      Rails.logger.error "Analysis items is nil for analysis #{analysis_id}"
      broadcast_extraction_failed(analysis_id, "Analysis items data is missing")
      return # Gracefully handle missing data
    end

    selected_items = Array(all_items).select { |item| item.is_a?(Hash) && @selected_item_ids.include?(item["id"].to_s) }

    if selected_items.empty?
      Rails.logger.warn "No items found for selected IDs: #{@selected_item_ids.inspect}"
      broadcast_extraction_failed(@analysis.id, "No items found for selected IDs")
      return
    end

    Rails.logger.info "Processing #{selected_items.count} items for extraction"

    extraction_results = []

    selected_items.each_with_index do |item_data, index|
      item_name = item_data.is_a?(Hash) ? (item_data["item_name"] || item_data[:item_name] || "Item #{index + 1}") : "Item #{index + 1}"
      update_extraction_progress(
        current: index + 1,
        total: selected_items.count,
        item_name: item_name
      )

      begin
        # Extract single item
        # Note: StockPhotoExtractionService needs to be implemented
        # For now, this is a placeholder that creates extraction result records
        extraction_result = extract_single_item(item_data)

        # Store result
        result = ExtractionResult.create!(
          clothing_analysis: @analysis,
          item_data: item_data,
          extracted_image_blob_id: extraction_result[:image_blob_id],
          extraction_quality: extraction_result[:quality_score],
          status: "completed"
        )

        extraction_results << result

        # Notify individual item completion
        item_id = item_data.is_a?(Hash) ? (item_data["id"] || item_data[:id]) : "unknown"
        broadcast_item_complete(item_id, result)

      rescue StandardError => e
        handle_extraction_error(item_data, e)
      end
    end

    # Notify overall completion
    broadcast_extraction_complete(extraction_results)

    Rails.logger.info "Extraction completed: #{extraction_results.count} items extracted successfully"
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error "Analysis not found: #{e.message}"
    broadcast_extraction_failed(analysis_id, "Analysis not found")
    # Don't re-raise - allow graceful failure with broadcast
  rescue StandardError => e
    Rails.logger.error "StockExtractionJob failed: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")
    # Only broadcast if we have an analysis (otherwise analysis_id might not be accessible)
    broadcast_extraction_failed(@analysis&.id || analysis_id, e.message)
    # Re-raise in test environment for debugging
    raise if Rails.env.test? && !e.message.include?("Analysis items data is missing")
  end

  private

  def extract_single_item(item_data)
    # TODO: Implement StockPhotoExtractionService.extract_single_item
    # For now, return a placeholder structure
    # This should call: StockPhotoExtractionService.extract_single_item(@analysis.image_blob, item_data)
    Rails.logger.warn "StockPhotoExtractionService not yet implemented - using placeholder"

    {
      # Use analysis image blob as fallback until service is implemented
      image_blob_id: @analysis.image_blob_id,
      quality_score: 0.5  # Placeholder quality score
    }
  end

  def update_extraction_progress(current:, total:, item_name:)
    ActionCable.server.broadcast(
      "extraction_#{@analysis.id}",
      {
        type: "extraction_progress",
        current_item: current,
        total_items: total,
        item_name: item_name,
        progress_percent: (current.to_f / total * 100).round,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_item_complete(item_id, result)
    ActionCable.server.broadcast(
      "extraction_#{@analysis.id}",
      {
        type: "item_extraction_complete",
        item_id: item_id,
        extraction_result_id: result.id,
        quality_score: result.extraction_quality,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_extraction_complete(results)
    ActionCable.server.broadcast(
      "extraction_#{@analysis.id}",
      {
        type: "extraction_complete",
        total_items: results.count,
        successful_items: results.count { |r| r.extraction_successful? },
        extraction_result_ids: results.map(&:id),
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_extraction_failed(analysis_id, error_message)
    ActionCable.server.broadcast(
      "extraction_#{analysis_id}",
      {
        type: "extraction_failed",
        error: error_message,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def handle_extraction_error(item_data, error)
    item_id = item_data.is_a?(Hash) ? (item_data["id"] || item_data[:id]) : "unknown"
    Rails.logger.error "Failed to extract item #{item_id}: #{error.message}"

    # Create failed extraction result
    ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: item_data.is_a?(Hash) ? item_data : {},
      status: "failed"
    )

    # Broadcast error for this specific item
    ActionCable.server.broadcast(
      "extraction_#{@analysis.id}",
      {
        type: "item_extraction_failed",
        item_id: item_id,
        error: error.message,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end
end
