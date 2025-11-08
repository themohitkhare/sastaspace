module Services
  # Service for handling inventory item update workflow
  # Extracts update logic from InventoryItemsController
  class InventoryItemUpdateService
    attr_reader :inventory_item, :params

    def initialize(inventory_item:, params:)
      @inventory_item = inventory_item
      @params = params
    end

    # Update inventory item with all attachments
    # @return [Hash] Result hash with :success, :inventory_item, :errors
    def update
      # Extract blob_id before updating - it's not a model attribute
      item_params = inventory_item_params.except(:blob_id)

      if @inventory_item.update(item_params)
        # Normalize category/subcategory after update
        normalize_category_subcategory

        # Handle image attachments
        attachment_service = Services::BlobAttachmentService.new(inventory_item: @inventory_item)
        handle_image_attachments(attachment_service)

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
      # Permit metadata fields directly (store_accessor allows direct assignment)
      # Also permit metadata hash for nested structure
      @params.require(:inventory_item).permit(
        :name, :description, :category_id, :subcategory_id, :purchase_price, :purchase_date, :blob_id,
        :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes,
        metadata: [ :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes ]
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
        attachment_service.attach_additional_images_from_files(@params[:inventory_item][:additional_images])
      end
    end
  end
end
