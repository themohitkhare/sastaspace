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

    # Apply search
    if params[:search].present?
      search_term = "%#{params[:search]}%"
      @inventory_items = @inventory_items.where(
        "name ILIKE ? OR description ILIKE ?",
        search_term, search_term
      )
    end

    @categories = Category.active.order(:name)
  end

  def show
  end

  def new
    @inventory_item = current_user.inventory_items.build
    @categories = Category.active.order(:name)
  end

  def create
    @inventory_item = current_user.inventory_items.build(inventory_item_params)
    @categories = Category.active.order(:name)

    # Handle metadata fields from form
    if params[:inventory_item]
      metadata = {}
      metadata["color"] = params[:inventory_item][:color] if params[:inventory_item][:color].present?
      metadata["size"] = params[:inventory_item][:size] if params[:inventory_item][:size].present?
      @inventory_item.metadata = metadata if metadata.any?
    end

    if @inventory_item.save
      # Handle image uploads
      @inventory_item.primary_image.attach(params[:inventory_item][:primary_image]) if params[:inventory_item] && params[:inventory_item][:primary_image].present?

      if params[:inventory_item] && params[:inventory_item][:additional_images].present?
        Array(params[:inventory_item][:additional_images]).each do |image|
          @inventory_item.additional_images.attach(image)
        end
      end

      redirect_to @inventory_item, notice: "Item created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @categories = Category.active.order(:name)
  end

  def update
    # Handle metadata fields from form
    if params[:inventory_item]
      metadata = @inventory_item.metadata || {}
      metadata["color"] = params[:inventory_item][:color] if params[:inventory_item].key?(:color)
      metadata["size"] = params[:inventory_item][:size] if params[:inventory_item].key?(:size)
      @inventory_item.metadata = metadata
    end

    if @inventory_item.update(inventory_item_params.except(:color, :size))
      # Handle image uploads
      @inventory_item.primary_image.attach(params[:inventory_item][:primary_image]) if params[:inventory_item] && params[:inventory_item][:primary_image].present?

      if params[:inventory_item] && params[:inventory_item][:additional_images].present?
        Array(params[:inventory_item][:additional_images]).each do |image|
          @inventory_item.additional_images.attach(image)
        end
      end

      redirect_to @inventory_item, notice: "Item updated successfully"
    else
      @categories = Category.active.order(:name)
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @inventory_item.destroy
    redirect_to inventory_items_path, notice: "Item deleted successfully"
  end

  private

  def set_inventory_item
    @inventory_item = current_user.inventory_items.find(params[:id])
  end

  def inventory_item_params
    params.require(:inventory_item).permit(
      :name, :description, :category_id, :item_type, :purchase_price, :purchase_date,
      metadata: [ :color, :size, :material, :season, :occasion, :care_instructions, :fit_notes, :style_notes ]
    )
  end
end
