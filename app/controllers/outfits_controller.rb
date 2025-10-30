class OutfitsController < ApplicationController
  before_action :require_login
  before_action :set_outfit, only: [ :show, :edit ]

  def index
    @outfits = current_user.outfits.order(created_at: :desc)
  end

  def show
  end

  def new
    @outfit = current_user.outfits.new
  end

  def create
    @outfit = current_user.outfits.new(outfit_params)
    if @outfit.save
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

  private

  def set_outfit
    @outfit = current_user.outfits.find(params[:id])
  end

  def require_login
    redirect_to login_path unless respond_to?(:current_user) && current_user.present?
  end

  def outfit_params
    params.require(:outfit).permit(:name, :description, :occasion)
  end
end
