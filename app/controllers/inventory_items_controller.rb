class InventoryItemsController < ApplicationController
  include SessionAuthenticable

  before_action :authenticate_user!
  before_action :set_inventory_item, only: [ :show, :edit, :update, :destroy ]

  def index
    @inventory_items = current_user.inventory_items
                                   .includes(:category, :brand, primary_image_attachment: :blob)
                                   .order(created_at: :desc)

    # Apply filters
    @inventory_items = @inventory_items.where(category_id: params[:category_id]) if params[:category_id].present?
    # Removed item_type filtering; derive from category hierarchy if needed

    # Filter by color (metadata)
    if params[:color].present?
      @inventory_items = @inventory_items.where(Arel.sql("metadata->>'color' ILIKE ?"), "%#{params[:color]}%")
    end

    # Filter by season (metadata)
    if params[:season].present?
      @inventory_items = @inventory_items.where(Arel.sql("metadata->>'season' = ?"), params[:season])
    end

    # Apply search
    if params[:search].present?
      search_term = "%#{params[:search]}%"
      @inventory_items = @inventory_items.where(
        Arel.sql("name ILIKE ? OR description ILIKE ?"),
        search_term, search_term
      )
    end

    @categories = Category.active.order(:name)

    # Get unique colors and seasons for filter dropdowns
    @available_colors = current_user.inventory_items
      .where(Arel.sql("metadata->>'color' IS NOT NULL AND metadata->>'color' != ''"))
      .distinct
      .pluck(Arel.sql("metadata->>'color'"))
      .compact
      .uniq
      .sort

    @available_seasons = %w[spring summer fall winter all-season]

    # Paginate results
    @inventory_items = @inventory_items.page(params[:page]).per(24) # 24 items per page (good for grid/list views)
  end

  def show
    redirect_to edit_inventory_item_path(@inventory_item)
  end

  def new
    @inventory_item = current_user.inventory_items.build
    @categories = Category.active.order(:name)
  end

  def new_ai
    @inventory_item = current_user.inventory_items.build
    @categories = Category.active.order(:name)
  end

  def create
    # Extract blob_id before building - it's not a model attribute
    blob_id = params[:inventory_item]&.dig(:blob_id) || params.dig(:inventory_item, :blob_id)
    
    # Build item without blob_id (it's not a model attribute)
    item_params = inventory_item_params.except(:blob_id)
    @inventory_item = current_user.inventory_items.build(item_params)
    @categories = Category.active.order(:name)

    # Normalize category/subcategory: if a selected category has a parent, treat it as subcategory
    if @inventory_item.category_id.present?
      selected = Category.find_by(id: @inventory_item.category_id)
      if selected&.parent_id.present?
        @inventory_item.subcategory_id = selected.id
        # set category to top-level ancestor
        node = selected
        node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
        @inventory_item.category_id = node&.id || selected.id
      end
    end

    if @inventory_item.save
      # Handle blob_id from AI upload (attach existing blob)
      Rails.logger.info "Checking for blob_id in params. Present: #{blob_id.present?}, Value: #{blob_id}"
      
      # Also check for blob_id in session if not in params (fallback for AI uploads)
      blob_id ||= session[:pending_blob_id] if session[:pending_blob_id].present?
      
      if blob_id.present?
        begin
          # Convert to integer to ensure proper lookup
          blob_id_int = blob_id.to_i
          blob = ActiveStorage::Blob.find_by(id: blob_id_int)
          
          unless blob
            Rails.logger.error "Blob #{blob_id_int} not found in database"
          end
          
          if blob
            # Explicitly create attachment with correct name to ensure it's "primary_image" not "attachments"
            @inventory_item.primary_image_attachment&.purge # Remove existing if any
            @inventory_item.primary_image.attach(blob)
            
            # Note: ActiveStorage attachments are persisted automatically when attach() is called
            # No need to explicitly save as attach() creates the attachment record directly
            
            Rails.logger.info "Successfully attached blob #{blob.id} as primary image for inventory item #{@inventory_item.id}"

            # Reload and verify attachment was created correctly
            @inventory_item.reload
            attachment = @inventory_item.primary_image_attachment
            if attachment && attachment.persisted?
              Rails.logger.info "Attachment verified: name=#{attachment.name}, blob_id=#{attachment.blob_id}, record=#{attachment.record_type}##{attachment.record_id}"
              # Clear session blob_id if it was used
              session.delete(:pending_blob_id) if session[:pending_blob_id].to_s == blob_id_int.to_s
            else
              Rails.logger.error "Attachment not found or not persisted after attach! Item ID: #{@inventory_item.id}, Blob ID: #{blob.id}"
              # Try attaching again as fallback
              @inventory_item.primary_image.attach(blob)
              @inventory_item.reload
              
              # Final verification
              if @inventory_item.primary_image_attachment&.persisted?
                Rails.logger.info "Attachment succeeded on retry"
              else
                Rails.logger.error "Attachment FAILED even after retry!"
              end
            end
          else
            Rails.logger.error "Could not find blob with ID #{blob_id_int} for inventory item #{@inventory_item.id}"
          end
        rescue ActiveRecord::RecordNotFound => e
          Rails.logger.error "Blob #{blob_id_int} not found for inventory item: #{e.message}"
        rescue StandardError => e
          Rails.logger.error "Error attaching blob to inventory item: #{e.message}"
          Rails.logger.error e.backtrace.first(5).join("\n")
        end
      else
        Rails.logger.warn "No blob_id found in params or session for inventory item #{@inventory_item.id}"
      end

      # Handle image uploads (fallback if blob_id not present) - with deduplication
      if params[:inventory_item] && params[:inventory_item][:primary_image].present?
        blob = Services::BlobDeduplicationService.find_or_create_blob(
          io: params[:inventory_item][:primary_image].open,
          filename: params[:inventory_item][:primary_image].original_filename,
          content_type: params[:inventory_item][:primary_image].content_type
        )
        @inventory_item.primary_image_attachment&.purge # Remove existing if any
        @inventory_item.primary_image.attach(blob)
      end

      if params[:inventory_item] && params[:inventory_item][:additional_images].present?
        Array(params[:inventory_item][:additional_images]).reject(&:blank?).each do |image|
          # Skip if not an uploaded file (could be empty string)
          next unless image.is_a?(ActionDispatch::Http::UploadedFile)

          blob = Services::BlobDeduplicationService.find_or_create_blob(
            io: image.open,
            filename: image.original_filename,
            content_type: image.content_type
          )
          @inventory_item.additional_images.attach(blob)
        end
      end

      redirect_to inventory_items_path, notice: "Item created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @categories = Category.active.order(:name)
  end

  def update
    if @inventory_item.update(inventory_item_params)
      # Normalize category/subcategory after update
      if @inventory_item.category_id.present?
        selected = Category.find_by(id: @inventory_item.category_id)
        if selected&.parent_id.present?
          @inventory_item.update_column(:subcategory_id, selected.id)
          node = selected
          node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
          @inventory_item.update_column(:category_id, node&.id || selected.id)
        end
      end

      # Handle blob_id from AI upload (only attach if not already attached)
      blob_id_param = params[:inventory_item]&.dig(:blob_id)
      if blob_id_param.present? && !@inventory_item.primary_image.attached?
        begin
          # Convert to integer to ensure proper lookup
          blob_id_int = blob_id_param.to_i
          blob = ActiveStorage::Blob.find_by(id: blob_id_int)
          
          if blob
            # Explicitly create attachment with correct name
            @inventory_item.primary_image.attach(blob)
            # Note: ActiveStorage attachments are persisted automatically when attach() is called
            @inventory_item.reload

            # Verify attachment was created correctly
            attachment = @inventory_item.primary_image_attachment
            if attachment && attachment.persisted?
              Rails.logger.info "Attachment verified on update: name=#{attachment.name}, blob_id=#{attachment.blob_id}"
            else
              Rails.logger.error "Attachment not found or not persisted after attach on update! Item ID: #{@inventory_item.id}, Blob ID: #{blob.id}"
            end
          else
            Rails.logger.warn "Blob #{blob_id_int} not found in database"
          end
        rescue StandardError => e
          Rails.logger.error "Error attaching blob on update: #{e.message}"
          Rails.logger.error e.backtrace.first(5).join("\n")
        end
      end

      # Handle image uploads (fallback if blob_id not present) - with deduplication
      if params[:inventory_item] && params[:inventory_item][:primary_image].present?
        blob = Services::BlobDeduplicationService.find_or_create_blob(
          io: params[:inventory_item][:primary_image].open,
          filename: params[:inventory_item][:primary_image].original_filename,
          content_type: params[:inventory_item][:primary_image].content_type
        )
        @inventory_item.primary_image_attachment&.purge # Remove existing if any
        @inventory_item.primary_image.attach(blob)
      end

      if params[:inventory_item] && params[:inventory_item][:additional_images].present?
        Array(params[:inventory_item][:additional_images]).reject(&:blank?).each do |image|
          # Skip if not an uploaded file (could be empty string)
          next unless image.is_a?(ActionDispatch::Http::UploadedFile)

          blob = Services::BlobDeduplicationService.find_or_create_blob(
            io: image.open,
            filename: image.original_filename,
            content_type: image.content_type
          )
          @inventory_item.additional_images.attach(blob)
        end
      end

      redirect_to inventory_items_path, notice: "Item updated successfully"
    else
      @categories = Category.active.order(:name)
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @inventory_item.destroy
    redirect_to inventory_items_path, notice: "Item deleted successfully"
  end

  def bulk_delete
    item_ids = params[:item_ids] || []
    items = current_user.inventory_items.where(id: item_ids)
    count = items.count

    if count > 0
      items.destroy_all
      redirect_to inventory_items_path, notice: "#{count} item(s) deleted successfully"
    else
      redirect_to inventory_items_path, alert: "No items selected for deletion"
    end
  end

  private

  def set_inventory_item
    @inventory_item = current_user.inventory_items.find(params[:id])
  end

  def inventory_item_params
    params.require(:inventory_item).permit(
      :name, :description, :category_id, :subcategory_id, :purchase_price, :purchase_date, :blob_id,
      metadata: [ :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes ]
    )
  end
end
