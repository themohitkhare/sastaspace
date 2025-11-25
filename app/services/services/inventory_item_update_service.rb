module Services
  # Service for handling inventory item update workflow
  # Extracts update logic from InventoryItemsController
  class InventoryItemUpdateService
    attr_reader :inventory_item, :params

    # Fields that should trigger stock photo extraction retrigger
    EXTRACTION_RELEVANT_FIELDS = [
      :description,
      :category_id,
      :subcategory_id,
      :color,
      :size,
      :material,
      :season,
      :occasion,
      :care_instructions,
      :fit_notes,
      :style_notes,
      :extraction_prompt
    ].freeze

    # Store accessor fields (stored in metadata JSON, not as direct attributes)
    STORE_ACCESSOR_FIELDS = %i[color size material season occasion care_instructions fit_notes style_notes].freeze

    def initialize(inventory_item:, params:)
      @inventory_item = inventory_item
      @params = params
      @original_attributes = @inventory_item.attributes.dup
      @initial_additional_images_count = @inventory_item.additional_images.count
    end

    # Update inventory item with all attachments
    # @return [Hash] Result hash with :success, :inventory_item, :errors
    def update
      # Extract image-related params before updating - we handle them explicitly afterward
      item_params = inventory_item_params.except(:blob_id, :primary_image, :additional_images)

      # Handle metadata merging - merge incoming metadata with existing instead of replacing
      if item_params[:metadata].present?
        existing_metadata = @inventory_item.metadata || {}
        item_params[:metadata] = existing_metadata.merge(item_params[:metadata])
      end

      if @inventory_item.update(item_params)
        # Normalize category/subcategory after update
        normalize_category_subcategory

        # Handle image attachments
        attachment_service = Services::BlobAttachmentService.new(inventory_item: @inventory_item)
        additional_images_added = handle_image_attachments(attachment_service)

        # Reload to ensure we have the latest state for comparison (after attachments)
        # This reload is needed for accurate field comparison in should_retrigger_extraction?
        @inventory_item.reload

        # Retrigger stock photo extraction if relevant fields changed
        if should_retrigger_extraction?(additional_images_added)
          retrigger_stock_photo_extraction
        end

        {
          success: true,
          inventory_item: @inventory_item,
          errors: nil
        }
      else
        {
          success: false,
          inventory_item: @inventory_item,
          errors: @inventory_item.errors
        }
      end
    end

    private

    def inventory_item_params
      # Permit both individual metadata fields (for store_accessor) and nested metadata hash
      # Also permit image uploads for API compatibility
      @params.require(:inventory_item).permit(
        :name, :description, :category_id, :subcategory_id, :purchase_price, :purchase_date, :blob_id,
        :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes,
        :primary_image, :extraction_prompt,
        additional_images: [],
        metadata: {}
      )
    end

    def normalize_category_subcategory
      return unless @inventory_item.category_id.present?

      selected = Category.find_by(id: @inventory_item.category_id)
      return unless selected&.parent_id.present?

      @inventory_item.update_column(:subcategory_id, selected.id)
      node = selected
      node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
      @inventory_item.update_column(:category_id, node&.id || selected.id)
    end

    def handle_image_attachments(attachment_service)
      additional_images_added = false

      # Handle blob_id from AI upload (only attach if not already attached)
      blob_id_param = @params[:inventory_item]&.dig(:blob_id)
      if blob_id_param.present? && !@inventory_item.primary_image.attached?
        attachment_service.attach_primary_image_from_blob_id(blob_id_param)
      end

      # Handle image uploads (fallback if blob_id not present) - with deduplication
      if @params[:inventory_item] && @params[:inventory_item][:primary_image].present?
        attachment_service.attach_primary_image_from_file(@params[:inventory_item][:primary_image])
      end

      if @params[:inventory_item] && @params[:inventory_item][:additional_images].present?
        # Reload to ensure accurate state after update and any primary image attachment
        @inventory_item.reload
        count_before = @inventory_item.additional_images.count
        count_attached = attachment_service.attach_additional_images_from_files(@params[:inventory_item][:additional_images])
        # attach_additional_images_from_files already reloads the item
        # additional_images_added is true if we actually attached images (count increased)
        additional_images_added = count_attached > 0
      end

      additional_images_added
    end

    # Check if stock photo extraction should be retriggered
    def should_retrigger_extraction?(additional_images_added)
      # Only retrigger if item has a primary image
      return false unless @inventory_item.primary_image.attached?

      # Check if any extraction-relevant fields changed
      # For store_accessor fields (stored in metadata), compare from metadata hash
      relevant_fields_changed = EXTRACTION_RELEVANT_FIELDS.any? do |field|
        # Store accessor fields are in metadata, regular fields are in attributes
        if STORE_ACCESSOR_FIELDS.include?(field)
          # Compare from metadata hash
          original_metadata = @original_attributes["metadata"] || {}
          new_metadata = @inventory_item.metadata || {}
          original_value = original_metadata[field.to_s]
          new_value = new_metadata[field.to_s]
        else
          # Regular attribute field
          original_value = @original_attributes[field.to_s]
          new_value = @inventory_item.send(field)
        end
        original_value != new_value
      end

      # Retrigger if relevant fields changed or additional images added
      relevant_fields_changed || additional_images_added
    end

    # Retrigger stock photo extraction with updated item data
    def retrigger_stock_photo_extraction
      begin
        job_id = StockPhotoExtractionService.queue_for_item(@inventory_item, clear_completion_timestamp: true)
        Rails.logger.info "[InventoryItemUpdate] Retriggered stock photo extraction for item #{@inventory_item.id} (job: #{job_id})" if job_id
      rescue StandardError => e
        Rails.logger.error "[InventoryItemUpdate] Failed to retrigger extraction for item #{@inventory_item.id}: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
        # Don't fail the update if extraction retrigger fails
      end
    end
  end
end
