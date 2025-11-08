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
    @categories = Category.active.order(:name)

    begin
      result = Services::InventoryItemCreationService.new(
        user: current_user,
        params: params,
        session: session
      ).create

      @inventory_item = result[:inventory_item]

      if result[:success]
        redirect_to inventory_items_path, notice: "Item created successfully"
      else
        render :new, status: :unprocessable_entity
      end
    rescue StandardError => e
      Rails.logger.error "Error in create action: #{e.message}"
      Rails.logger.error e.backtrace.first(10).join("\n")
      @inventory_item = current_user.inventory_items.build(inventory_item_params.except(:blob_id))
      @inventory_item.errors.add(:base, "An error occurred: #{e.message}")
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @categories = Category.active.order(:name)
  end

  def update
    result = Services::InventoryItemUpdateService.new(
      inventory_item: @inventory_item,
      params: params
    ).update

    if result[:success]
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
