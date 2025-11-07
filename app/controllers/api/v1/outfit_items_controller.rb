module Api
  module V1
    class OutfitItemsController < BaseController
      before_action :set_outfit
      before_action :set_outfit_item, only: [ :destroy, :update_styling_notes ]

      def create
        inventory_item = current_user.inventory_items.find_by(id: params[:inventory_item_id])

        unless inventory_item
          return render json: {
            success: false,
            error: {
              code: "INVALID_ITEM",
              message: "Inventory item not found or doesn't belong to you"
            },
            timestamp: Time.current
          }, status: :not_found
        end

        outfit_item = @outfit.outfit_items.build(
          inventory_item: inventory_item,
          position: params[:position] || @outfit.outfit_items.count
        )

        if outfit_item.save
          render json: {
            success: true,
            data: { outfit_item: serialize_outfit_item(outfit_item) },
            message: "Item added to outfit",
            timestamp: Time.current
          }, status: :created
        else
          render json: {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              details: outfit_item.errors.full_messages
            },
            timestamp: Time.current
          }, status: :unprocessable_entity
        end
      end

      def destroy
        @outfit_item.destroy
        render json: {
          success: true,
          data: {},
          message: "Item removed from outfit",
          timestamp: Time.current
        }
      end

      def update_styling_notes
        if @outfit_item.update(styling_notes: params[:styling_notes])
          render json: {
            success: true,
            data: { outfit_item: serialize_outfit_item(@outfit_item) },
            message: "Styling notes updated",
            timestamp: Time.current
          }
        else
          render json: {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              details: @outfit_item.errors.full_messages
            },
            timestamp: Time.current
          }, status: :unprocessable_entity
        end
      end

      private

      def set_outfit
        @outfit = current_user.outfits.find(params[:outfit_id])
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "NOT_FOUND",
            message: "Outfit not found"
          },
          timestamp: Time.current
        }, status: :not_found
        false # Prevent further action
      end

      def set_outfit_item
        @outfit_item = @outfit.outfit_items.find(params[:id])
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "NOT_FOUND",
            message: "Outfit item not found"
          },
          timestamp: Time.current
        }, status: :not_found
        false # Prevent further action
      end

      def serialize_outfit_item(outfit_item)
        {
          id: outfit_item.id,
          outfit_id: outfit_item.outfit_id,
          inventory_item_id: outfit_item.inventory_item_id,
          position: outfit_item.position,
          styling_notes: outfit_item.styling_notes,
          worn_count: outfit_item.worn_count,
          last_worn_at: outfit_item.last_worn_at,
          inventory_item: {
            id: outfit_item.inventory_item.id,
            name: outfit_item.inventory_item.name,
            category: outfit_item.inventory_item.category&.name
          }
        }
      end
    end
  end
end
