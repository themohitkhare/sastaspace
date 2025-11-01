class OutfitsController < ApplicationController
  before_action :authenticate_user!
  before_action :set_outfit, only: [ :show, :edit ]

  def index
    @outfits = current_user.outfits.includes(:outfit_items, outfit_items: :inventory_item).order(created_at: :desc)

    # Apply filters
    @outfits = @outfits.where(occasion: params[:occasion]) if params[:occasion].present?
    @outfits = @outfits.where(is_favorite: true) if params[:favorite] == "true"

    # Filter by date range
    if params[:date_range].present?
      case params[:date_range]
      when "today"
        @outfits = @outfits.where("created_at >= ?", Time.current.beginning_of_day)
      when "week"
        @outfits = @outfits.where("created_at >= ?", 1.week.ago)
      when "month"
        @outfits = @outfits.where("created_at >= ?", 1.month.ago)
      when "year"
        @outfits = @outfits.where("created_at >= ?", 1.year.ago)
      end
    end

    # Search by name
    if params[:search].present?
      search_term = "%#{params[:search]}%"
      @outfits = @outfits.where("name ILIKE ? OR description ILIKE ?", search_term, search_term)
    end

    # Sort options
    case params[:sort]
    when "name_asc"
      @outfits = @outfits.order(name: :asc)
    when "name_desc"
      @outfits = @outfits.order(name: :desc)
    when "recent"
      @outfits = @outfits.order(created_at: :desc)
    when "oldest"
      @outfits = @outfits.order(created_at: :asc)
    else
      @outfits = @outfits.order(created_at: :desc) # Default
    end

    # Get unique occasions for filter dropdown
    @available_occasions = current_user.outfits.where.not(occasion: nil).distinct.pluck(:occasion).compact.sort

    # Paginate if requested
    if params[:per_page].present?
      @outfits = @outfits.page(params[:page]).per(params[:per_page])
    end
  end

  def show
  end

  def new
    @outfit = current_user.outfits.new
  end

  def create
    # Extract inventory_item_ids before building (not a direct model attribute)
    inventory_item_ids = params[:outfit]&.dig(:inventory_item_ids) || []
    inventory_item_ids = Array(inventory_item_ids).map(&:to_i).reject(&:zero?)

    @outfit = current_user.outfits.new(outfit_params.except(:inventory_item_ids))

    if @outfit.save
      # Create outfit items if inventory_item_ids provided
      if inventory_item_ids.any?
        inventory_item_ids.each_with_index do |item_id, index|
          # Verify item belongs to current user
          inventory_item = current_user.inventory_items.find_by(id: item_id)
          if inventory_item
            @outfit.outfit_items.create!(
              inventory_item: inventory_item,
              position: index
            )
          end
        end
      end

      redirect_to outfit_path(@outfit), notice: "Outfit created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def builder
    @outfit = current_user.outfits.new
  end

  def inspiration
    @outfits = current_user.outfits.order(created_at: :desc).limit(12)
  end

  def new_from_photo
    @outfit = current_user.outfits.new
  end

  private

  def set_outfit
    @outfit = current_user.outfits.find(params[:id])
  end

  def outfit_params
    params.require(:outfit).permit(:name, :description, :occasion, inventory_item_ids: [])
  end
end
