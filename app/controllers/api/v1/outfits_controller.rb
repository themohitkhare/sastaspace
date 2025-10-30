module Api
  module V1
    class OutfitsController < ApplicationController
      include Authenticable
      skip_before_action :authenticate_user!, only: [ :index, :show ]
      before_action :authenticate_user_optional, only: [ :index, :show ]
      before_action :set_outfit, only: [ :show, :update, :destroy, :wear, :favorite, :suggestions, :duplicate ]

      def index
        outfits = current_user ? current_user.outfits : Outfit.none
        render json: { success: true, data: { outfits: serialize(outfits) }, message: "OK", timestamp: Time.current }
      end

      def show
        authorize_owner!
        render json: { success: true, data: { outfit: serialize(@outfit) }, message: "OK", timestamp: Time.current }
      end

      def create
        outfit = current_user.outfits.new(outfit_params)
        if outfit.save
          render json: { success: true, data: { outfit: serialize(outfit) }, message: "Created", timestamp: Time.current }, status: :created
        else
          render json: { success: false, error: { code: "VALIDATION_ERROR", details: outfit.errors.full_messages }, timestamp: Time.current }, status: :unprocessable_entity
        end
      end

      def update
        authorize_owner!
        if @outfit.update(outfit_params)
          render json: { success: true, data: { outfit: serialize(@outfit) }, message: "Updated", timestamp: Time.current }
        else
          render json: { success: false, error: { code: "VALIDATION_ERROR", details: @outfit.errors.full_messages }, timestamp: Time.current }, status: :unprocessable_entity
        end
      end

      def destroy
        authorize_owner!
        @outfit.destroy
        render json: { success: true, data: {}, message: "Deleted", timestamp: Time.current }
      end

      def wear
        authorize_owner!
        @outfit.update!(last_worn_at: Time.current) if @outfit.respond_to?(:last_worn_at)
        @outfit.increment!(:wear_count) if @outfit.respond_to?(:wear_count)
        render json: { success: true, data: { outfit: serialize(@outfit) }, message: "Wear recorded", timestamp: Time.current }
      end

      def favorite
        authorize_owner!
        @outfit.update!(is_favorite: !@outfit.is_favorite)
        render json: { success: true, data: { outfit: serialize(@outfit) }, message: "Favorite updated", timestamp: Time.current }
      end

      def suggestions
        authorize_owner!
        # Placeholder: integrate with VectorSearchService / AI later
        render json: { success: true, data: { items: [] }, message: "Suggestions", timestamp: Time.current }
      end

      def duplicate
        authorize_owner!
        dup_attrs = @outfit.attributes.slice("name", "description", "season", "occasion")
        dup = current_user.outfits.create!(dup_attrs.merge("name" => "#{@outfit.name} (Copy)"))
        # Items copy will be implemented when outfit_items schema is aligned
        render json: { success: true, data: { outfit: serialize(dup) }, message: "Duplicated", timestamp: Time.current }, status: :created
      end

      private

      def set_outfit
        @outfit = Outfit.find(params[:id])
      end

      def authorize_owner!
        raise ActiveRecord::RecordNotFound unless @outfit.user_id == current_user&.id
      end

      def outfit_params
        params.require(:outfit).permit(:name, :description, :is_favorite, :formality, :season, :occasion)
      end

      def serialize(outfit_or_collection)
        if outfit_or_collection.respond_to?(:map)
          outfit_or_collection.map { |o| serialize_one(o) }
        else
          serialize_one(outfit_or_collection)
        end
      end

      def serialize_one(o)
        data = {
          id: o.id,
          name: o.name,
          description: o.description,
          is_favorite: o.is_favorite,
          season: (o.respond_to?(:season) ? o.season : nil),
          occasion: o.occasion,
          wear_count: (o.respond_to?(:wear_count) ? o.wear_count : nil),
          last_worn_at: (o.respond_to?(:last_worn_at) ? o.last_worn_at : nil),
          items: []
        }
        data
      end
    end
  end
end
