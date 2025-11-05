class OutfitsController < ApplicationController
  before_action :authenticate_user!
  before_action :set_outfit, only: [ :show, :edit, :update, :destroy ]

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
    # Handle both array and single value, and filter out empty strings/nil
    raw_ids = params[:outfit]&.dig(:inventory_item_ids) || []
    inventory_item_ids = Array(raw_ids)
                         .reject { |id| id.blank? || id.to_s.strip.empty? }
                         .map(&:to_i)
                         .reject(&:zero?)

    # Debug logging
    Rails.logger.info "=== Outfit Create Debug ==="
    Rails.logger.info "Raw params: #{params[:outfit].inspect}"
    Rails.logger.info "inventory_item_ids param: #{params[:outfit]&.dig(:inventory_item_ids).inspect}"
    Rails.logger.info "Processed inventory_item_ids: #{inventory_item_ids.inspect}"

    @outfit = current_user.outfits.new(outfit_params.except(:inventory_item_ids))

    if @outfit.save
      Rails.logger.info "Outfit saved with ID: #{@outfit.id}"

      # Create outfit items if inventory_item_ids provided
      if inventory_item_ids.any?
        Rails.logger.info "Creating #{inventory_item_ids.count} outfit items"
        inventory_item_ids.each_with_index do |item_id, index|
          # Verify item belongs to current user
          inventory_item = current_user.inventory_items.find_by(id: item_id)
          if inventory_item
            outfit_item = @outfit.outfit_items.create!(
              inventory_item: inventory_item,
              position: index
            )
            Rails.logger.info "Created outfit_item ##{outfit_item.id} for inventory_item ##{item_id}"
          else
            Rails.logger.warn "Inventory item ##{item_id} not found or doesn't belong to user"
          end
        end
      else
        Rails.logger.warn "No inventory_item_ids provided - outfit_items table will be empty"
      end

      redirect_to outfit_path(@outfit), notice: "Outfit created successfully"
    else
      Rails.logger.error "Outfit save failed: #{@outfit.errors.full_messages.inspect}"
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    # Extract inventory_item_ids before building (not a direct model attribute)
    # Handle both array and single value, and filter out empty strings/nil
    raw_ids = params[:outfit]&.dig(:inventory_item_ids) || []
    inventory_item_ids = Array(raw_ids)
                         .reject { |id| id.blank? || id.to_s.strip.empty? }
                         .map(&:to_i)
                         .reject(&:zero?)

    # Debug logging
    Rails.logger.info "=== Outfit Update Debug ==="
    Rails.logger.info "Outfit ID: #{@outfit.id}"
    Rails.logger.info "Raw params: #{params[:outfit].inspect}"
    Rails.logger.info "inventory_item_ids param: #{params[:outfit]&.dig(:inventory_item_ids).inspect}"
    Rails.logger.info "Processed inventory_item_ids: #{inventory_item_ids.inspect}"

    if @outfit.update(outfit_params.except(:inventory_item_ids))
      # Clear existing outfit items
      @outfit.outfit_items.destroy_all
      Rails.logger.info "Cleared existing outfit_items"

      # Create new outfit items if inventory_item_ids provided
      if inventory_item_ids.any?
        Rails.logger.info "Creating #{inventory_item_ids.count} outfit items"
        inventory_item_ids.each_with_index do |item_id, index|
          # Verify item belongs to current user
          inventory_item = current_user.inventory_items.find_by(id: item_id)
          if inventory_item
            outfit_item = @outfit.outfit_items.create!(
              inventory_item: inventory_item,
              position: index
            )
            Rails.logger.info "Created outfit_item ##{outfit_item.id} for inventory_item ##{item_id}"
          else
            Rails.logger.warn "Inventory item ##{item_id} not found or doesn't belong to user"
          end
        end
      else
        Rails.logger.warn "No inventory_item_ids provided - outfit_items table will be empty"
      end

      redirect_to outfit_path(@outfit), notice: "Outfit updated successfully"
    else
      Rails.logger.error "Outfit update failed: #{@outfit.errors.full_messages.inspect}"
      render :edit, status: :unprocessable_entity
    end
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

  def destroy
    @outfit.destroy
    redirect_to outfits_path, notice: "Outfit deleted successfully"
  end

  private

  def set_outfit
    @outfit = current_user.outfits.find(params[:id])
  end

  def outfit_params
    params.require(:outfit).permit(:name, :description, :occasion, inventory_item_ids: [])
  end
end
