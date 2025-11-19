module Services
  # Service for handling inventory item creation workflow
  # Extracts creation logic from InventoryItemsController
  class InventoryItemCreationService
    attr_reader :user, :params, :session

    def initialize(user:, params:, session: nil)
      @user = user
      @params = params
      @session = session
    end

    # Create inventory item with all attachments
    # @return [Hash] Result hash with :success, :inventory_item, :errors
    def create
      # Extract blob_id before building - it's not a model attribute
      blob_id = @params[:inventory_item]&.dig(:blob_id) || @params.dig(:inventory_item, :blob_id)

      # Build item without blob_id and images (handled by service with deduplication)
      # We exclude primary_image and additional_images to prevent ActiveStorage from
      # automatically attaching them without deduplication.
      item_params = inventory_item_params.except(:blob_id, :primary_image, :additional_images)
      inventory_item = @user.inventory_items.build(item_params)

      # Normalize category/subcategory
      normalize_category_subcategory(inventory_item)

      if inventory_item.save
        # Handle image attachments
        attachment_service = Services::BlobAttachmentService.new(inventory_item: inventory_item, session: @session)
        handle_image_attachments(attachment_service, blob_id)

        # Reload to ensure attachments are available
        inventory_item.reload

        {
          success: true,
          inventory_item: inventory_item,
          errors: nil
        }
      else
        {
          success: false,
          inventory_item: inventory_item,
          errors: inventory_item.errors
        }
      end
    end

    private

    def inventory_item_params
      # Permit metadata fields directly (store_accessor allows direct assignment)
      # Also permit metadata hash for nested structure
      # Permit image uploads (primary_image and additional_images array)
      @params.require(:inventory_item).permit(
        :name, :description, :category_id, :subcategory_id, :purchase_price, :purchase_date, :blob_id,
        :primary_image, :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes,
        additional_images: [],
        metadata: [ :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes ]
      )
    end

    def normalize_category_subcategory(inventory_item)
      return unless inventory_item.category_id.present?

      selected = Category.find_by(id: inventory_item.category_id)
      return unless selected&.parent_id.present?

      inventory_item.subcategory_id = selected.id
      # Set category to top-level ancestor
      node = selected
      node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
      inventory_item.category_id = node&.id || selected.id
    end

    def handle_image_attachments(attachment_service, blob_id)
      # Handle blob_id from AI upload (attach existing blob)
      Rails.logger.info "Checking for blob_id in params. Present: #{blob_id.present?}, Value: #{blob_id}"

      # Try to attach from blob_id first (from params or session)
      # handle_blob_id_from_params_or_session will check both params and session
      attachment_service.handle_blob_id_from_params_or_session(blob_id)

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
