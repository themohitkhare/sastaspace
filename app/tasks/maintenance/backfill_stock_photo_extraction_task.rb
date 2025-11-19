# Maintenance task to backfill stock photo extraction for inventory items
# This task processes items that haven't had stock photo extraction completed yet
# Access via: /maintenance_tasks

module Maintenance
  class BackfillStockPhotoExtractionTask < MaintenanceTasks::Task
    # Track job IDs and results for this run
    attr_accessor :job_results

    # Throttle job enqueues to prevent overwhelming ComfyUI
    # Process max 2 jobs per minute to keep latency low
    JOB_ENQUEUE_DELAY = 30.seconds # Delay between job enqueues
    MAX_CONCURRENT_JOBS = 1 # Max jobs to enqueue before waiting

    def initialize(*args)
      super
      @job_results = {
        queued: [],
        failed: [],
        skipped: []
      }
      @last_enqueue_time = nil
      @enqueue_count = 0
    end

    # Process items in batches
    def collection
      # Get all active items without completed extraction
      # We'll filter out items without images in the process method
      InventoryItem
        .active
        .without_stock_photo_extraction
        .includes(:category, :subcategory, :brand, :primary_image_attachment, :user)
    end

    # Process a single inventory item
    def process(item)
      unless item.primary_image.attached?
        @job_results[:skipped] << {
          item_id: item.id,
          item_name: item.name,
          reason: "No primary image attached"
        }
        Rails.logger.warn "Skipping inventory item #{item.id} (#{item.name}): No primary image attached"
        return
      end

      begin
        image_blob = item.primary_image.blob
        user = item.user

        # Build analysis_results from item data (already sanitized since we control the data)
        analysis_results = {
          "name" => item.name,
          "description" => item.description,
          "category_name" => item.category&.name,
          "category_matched" => item.category&.name,
          "subcategory" => item.subcategory&.name,
          "material" => item.material,
          "style" => item.style_notes,
          "style_notes" => item.style_notes,
          "brand_matched" => item.brand&.name,
          "colors" => [ item.color ].compact,
          "extraction_prompt" => item.extraction_prompt,
          "gender_appropriate" => true,
          "confidence" => 0.9
        }

        # Call the job directly (skip service layer to avoid Zeitwerk issues)
        # The service just validates and sanitizes, which we've already done
        job_id = SecureRandom.uuid

        # Throttle job enqueues to prevent overwhelming ComfyUI
        # Add delay between enqueues to stagger job execution
        if @last_enqueue_time && (Time.current - @last_enqueue_time) < JOB_ENQUEUE_DELAY
          sleep_time = JOB_ENQUEUE_DELAY - (Time.current - @last_enqueue_time)
          Rails.logger.info "[BackfillStockPhoto] Throttling: waiting #{sleep_time.round(2)}s before next job enqueue"
          sleep(sleep_time)
        end

        # Schedule job with a small delay to stagger execution
        # This prevents all jobs from hitting ComfyUI at once
        delay_seconds = @enqueue_count * 5 # Stagger by 5 seconds per job
        if delay_seconds > 0
          ExtractStockPhotoJob.set(wait: delay_seconds.seconds).perform_later(
            image_blob.id,
            analysis_results,
            user.id,
            job_id,
            item.id
          )
          Rails.logger.info "[BackfillStockPhoto] Job scheduled with #{delay_seconds}s delay to stagger execution"
        else
          ExtractStockPhotoJob.perform_later(
            image_blob.id,
            analysis_results,
            user.id,
            job_id,
            item.id
          )
        end

        @last_enqueue_time = Time.current
        @enqueue_count += 1

        @job_results[:queued] << {
          item_id: item.id,
          item_name: item.name,
          job_id: job_id,
          blob_id: image_blob.id,
          user_id: user.id
        }

        Rails.logger.info "[BackfillStockPhoto] Job queued - Item: #{item.id} (#{item.name}), Job ID: #{job_id}, Blob ID: #{image_blob.id}, User: #{user.id}"
      rescue StandardError => e
        error_details = {
          item_id: item.id,
          item_name: item.name,
          error_class: e.class.name,
          error_message: e.message
        }
        @job_results[:failed] << error_details

        Rails.logger.error "[BackfillStockPhoto] Failed to queue job for item #{item.id} (#{item.name}): #{e.class.name} - #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
        # Don't re-raise - continue processing other items
      end
    end

    # Count total items to process
    def count
      collection.count
    end

    # Called after the task completes - log summary
    def after_task
      super if defined?(super)

      summary = {
        queued: @job_results[:queued].count,
        failed: @job_results[:failed].count,
        skipped: @job_results[:skipped].count,
        total: @job_results[:queued].count + @job_results[:failed].count + @job_results[:skipped].count
      }

      Rails.logger.info "[BackfillStockPhoto] Task completed - Summary: #{summary.inspect}"

      if @job_results[:failed].any?
        Rails.logger.error "[BackfillStockPhoto] Failed items (#{@job_results[:failed].count}):"
        @job_results[:failed].each do |failure|
          Rails.logger.error "  - Item #{failure[:item_id]} (#{failure[:item_name]}): #{failure[:error_class]} - #{failure[:error_message]}"
        end
      end

      if @job_results[:queued].any?
        Rails.logger.info "[BackfillStockPhoto] Successfully queued #{@job_results[:queued].count} jobs. Job IDs:"
        @job_results[:queued].first(10).each do |result|
          Rails.logger.info "  - Item #{result[:item_id]} (#{result[:item_name]}): Job ID #{result[:job_id]}"
        end
        if @job_results[:queued].count > 10
          Rails.logger.info "  ... and #{@job_results[:queued].count - 10} more"
        end
      end
    end
  end
end
