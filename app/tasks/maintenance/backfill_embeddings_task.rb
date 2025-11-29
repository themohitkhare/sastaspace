# Maintenance task to backfill vector embeddings for inventory items
# This task processes items that don't have embeddings yet
# Access via: /maintenance_tasks

module Maintenance
  class BackfillEmbeddingsTask < MaintenanceTasks::Task
    # Track results for this run
    attr_accessor :job_results

    def initialize(*args)
      super
      @job_results = {
        processed: [],
        failed: [],
        skipped: []
      }
    end

    # Process items in batches
    def collection
      # Get all items without embeddings
      InventoryItem
        .where(embedding_vector: nil)
        .includes(:category, :subcategory, :brand, :user)
    end

    # Process a single inventory item
    def process(item)
      begin
        # Generate embedding for the item
        vector = EmbeddingService.generate_for_item(item)

        if vector.present?
          # Validate vector dimensions before saving
          if vector.length != 1536
            @job_results[:failed] << {
              item_id: item.id,
              item_name: item.name,
              error_class: "DimensionMismatch",
              error_message: "Expected 1536 dimensions, got #{vector.length}"
            }
            Rails.logger.error "[BackfillEmbeddings] Dimension mismatch for item #{item.id} (#{item.name}): expected 1536, got #{vector.length}"
            return
          end

          item.update_column(:embedding_vector, vector)

          @job_results[:processed] << {
            item_id: item.id,
            item_name: item.name,
            user_id: item.user_id
          }

          Rails.logger.info "[BackfillEmbeddings] Generated embedding for item #{item.id} (#{item.name})"
        else
          @job_results[:skipped] << {
            item_id: item.id,
            item_name: item.name,
            reason: "EmbeddingService returned nil"
          }

          Rails.logger.warn "[BackfillEmbeddings] Skipping item #{item.id} (#{item.name}): No embedding generated"
        end
      rescue StandardError => e
        error_details = {
          item_id: item.id,
          item_name: item.name,
          error_class: e.class.name,
          error_message: e.message
        }
        @job_results[:failed] << error_details

        Rails.logger.error "[BackfillEmbeddings] Failed to generate embedding for item #{item.id} (#{item.name}): #{e.class.name} - #{e.message}"
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
        processed: @job_results[:processed].count,
        failed: @job_results[:failed].count,
        skipped: @job_results[:skipped].count,
        total: @job_results[:processed].count + @job_results[:failed].count + @job_results[:skipped].count
      }

      Rails.logger.info "[BackfillEmbeddings] Task completed - Summary: #{summary.inspect}"

      if @job_results[:failed].any?
        Rails.logger.error "[BackfillEmbeddings] Failed items (#{@job_results[:failed].count}):"
        @job_results[:failed].first(20).each do |failure|
          Rails.logger.error "  - Item #{failure[:item_id]} (#{failure[:item_name]}): #{failure[:error_class]} - #{failure[:error_message]}"
        end
        if @job_results[:failed].count > 20
          Rails.logger.error "  ... and #{@job_results[:failed].count - 20} more failures"
        end
      end

      if @job_results[:processed].any?
        Rails.logger.info "[BackfillEmbeddings] Successfully processed #{@job_results[:processed].count} items:"
        @job_results[:processed].first(10).each do |result|
          Rails.logger.info "  - Item #{result[:item_id]} (#{result[:item_name]})"
        end
        if @job_results[:processed].count > 10
          Rails.logger.info "  ... and #{@job_results[:processed].count - 10} more"
        end
      end

      if @job_results[:skipped].any?
        Rails.logger.warn "[BackfillEmbeddings] Skipped #{@job_results[:skipped].count} items:"
        @job_results[:skipped].first(10).each do |result|
          Rails.logger.warn "  - Item #{result[:item_id]} (#{result[:item_name]}): #{result[:reason]}"
        end
        if @job_results[:skipped].count > 10
          Rails.logger.warn "  ... and #{@job_results[:skipped].count - 10} more"
        end
      end
    end
  end
end
