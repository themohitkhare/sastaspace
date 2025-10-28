module Api
  module V1
    class InventoryItemsController < ApplicationController
      include Authenticable

      before_action :authenticate_user!
      before_action :set_inventory_item, only: [ :show, :update, :destroy, :worn, :similar ]
      
      rescue_from ActionDispatch::Http::Parameters::ParseError, with: :handle_parse_error

      # GET /api/v1/inventory_items
      def index
        @inventory_items = current_user.inventory_items
                                      .includes(:category, :brand, :tags,
                                                primary_image_attachment: :blob,
                                                additional_images_attachments: :blob)
                                      .page(params[:page])
                                      .per(params[:per_page] || 20)

        # Apply filters
        @inventory_items = apply_filters(@inventory_items)

        render json: {
          success: true,
          data: {
            inventory_items: @inventory_items.map { |item| serialize_inventory_item(item) },
            pagination: {
              current_page: @inventory_items.current_page,
              total_pages: @inventory_items.total_pages,
              total_count: @inventory_items.total_count,
              per_page: @inventory_items.limit_value
            }
          },
          message: "Inventory items retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/inventory_items/:id
      def show
        render json: {
          success: true,
          data: {
            inventory_item: serialize_inventory_item(@inventory_item)
          },
          message: "Inventory item retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # POST /api/v1/inventory_items
      def create
        @inventory_item = current_user.inventory_items.build(inventory_item_params)

        if @inventory_item.save
          render json: {
            success: true,
            data: {
              inventory_item: serialize_inventory_item(@inventory_item)
            },
            message: "Inventory item created successfully",
            timestamp: Time.current.iso8601
          }, status: :created
        else
          render json: {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Inventory item creation failed",
              details: @inventory_item.errors.as_json
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        end
      end

      # PATCH /api/v1/inventory_items/:id
      def update
        if @inventory_item.update(inventory_item_params)
          render json: {
            success: true,
            data: {
              inventory_item: serialize_inventory_item(@inventory_item)
            },
            message: "Inventory item updated successfully",
            timestamp: Time.current.iso8601
          }
        else
          render json: {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Inventory item update failed",
              details: @inventory_item.errors.as_json
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        end
      end

      # DELETE /api/v1/inventory_items/:id
      def destroy
        if @inventory_item.destroy
          render json: {
            success: true,
            message: "Inventory item deleted successfully",
            timestamp: Time.current.iso8601
          }
        else
          render json: {
            success: false,
            error: {
              code: "DELETE_ERROR",
              message: "Failed to delete inventory item",
              details: @inventory_item.errors.as_json
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        end
      end

      # PATCH /api/v1/inventory_items/:id/worn
      def worn
        @inventory_item.increment_wear_count!

        render json: {
          success: true,
          data: {
            inventory_item: serialize_inventory_item(@inventory_item)
          },
          message: "Wear count updated successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/inventory_items/:id/similar
      def similar
        limit = params[:limit]&.to_i || 10
        similar_items = @inventory_item.find_similar_items(limit: limit)

        render json: {
          success: true,
          data: {
            similar_items: similar_items.map { |item| serialize_inventory_item(item) },
            base_item: serialize_inventory_item(@inventory_item)
          },
          message: "Similar items retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # POST /api/v1/inventory_items/semantic_search
      def semantic_search
        query = params[:q]&.strip
        return render_search_error("Search query required") if query.blank?

        limit = params[:limit]&.to_i || 20
        items = VectorSearchService.semantic_search(current_user, query, limit: limit)

        render json: {
          success: true,
          data: {
            inventory_items: items.map { |item| serialize_inventory_item(item) },
            query: query,
            total_results: items.count
          },
          message: "Semantic search completed successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/inventory_items/search
      def search
        query = params[:q]
        return render_search_error("Query parameter is required") unless query.present?

        @inventory_items = current_user.inventory_items
                                      .includes(:category, :brand, :tags,
                                                primary_image_attachment: :blob,
                                                additional_images_attachments: :blob)
                                      .where("name ILIKE ? OR description ILIKE ?", "%#{query}%", "%#{query}%")
                                      .page(params[:page])
                                      .per(params[:per_page] || 20)

        render json: {
          success: true,
          data: {
            inventory_items: @inventory_items.map { |item| serialize_inventory_item(item) },
            pagination: {
              current_page: @inventory_items.current_page,
              total_pages: @inventory_items.total_pages,
              total_count: @inventory_items.total_count,
              per_page: @inventory_items.limit_value
            },
            query: query
          },
          message: "Search completed successfully",
          timestamp: Time.current.iso8601
        }
      end

      # POST /api/v1/inventory_items/:id/primary_image
      def attach_primary_image
        if params[:image].present?
          @inventory_item.primary_image.attach(params[:image])
          render json: {
            success: true,
            data: {
              image_url: url_for(@inventory_item.primary_image)
            },
            message: "Primary image attached successfully",
            timestamp: Time.current.iso8601
          }
        else
          render json: {
            success: false,
            error: {
              code: "MISSING_IMAGE",
              message: "Image file is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end
      end

      # POST /api/v1/inventory_items/:id/additional_images
      def attach_additional_images
        if params[:images].present?
          @inventory_item.additional_images.attach(params[:images])
          render json: {
            success: true,
            data: {
              image_urls: @inventory_item.additional_images.map { |img| url_for(img) }
            },
            message: "Additional images attached successfully",
            timestamp: Time.current.iso8601
          }
        else
          render json: {
            success: false,
            error: {
              code: "MISSING_IMAGES",
              message: "Image files are required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end
      end

      # DELETE /api/v1/inventory_items/:id/primary_image
      def detach_primary_image
        @inventory_item.primary_image.purge
        render json: {
          success: true,
          message: "Primary image removed successfully",
          timestamp: Time.current.iso8601
        }
      end

      # DELETE /api/v1/inventory_items/:id/additional_images/:image_id
      def detach_additional_image
        image = @inventory_item.additional_images.find(params[:image_id])
        image.purge
        render json: {
          success: true,
          message: "Additional image removed successfully",
          timestamp: Time.current.iso8601
        }
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "NOT_FOUND",
            message: "Image not found"
          },
          timestamp: Time.current.iso8601
        }, status: :not_found
      end

      private

      def set_inventory_item
        @inventory_item = current_user.inventory_items
                                      .includes(:category, :brand, :tags,
                                                primary_image_attachment: :blob,
                                                additional_images_attachments: :blob)
                                      .find(params[:id])
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "NOT_FOUND",
            message: "Inventory item not found"
          },
          timestamp: Time.current.iso8601
        }, status: :not_found
      end

      def inventory_item_params
        begin
          permitted = params.require(:inventory_item).permit(
            :name, :item_type, :description, :status, :category_id, :brand_id,
            :purchase_price, :purchase_date, :primary_image, additional_images: [],
            metadata: {}, # Allow any metadata hash structure
            tag_ids: []
          )
          permitted
        rescue ActionController::ParameterMissing => e
          Rails.logger.error "Parameter missing: #{e.message}"
          raise
        rescue StandardError => e
          Rails.logger.error "Error parsing parameters: #{e.message}"
          raise
        end
      end

      def handle_parse_error(exception)
        Rails.logger.error "Parse error: #{exception.message}"
        render json: {
          success: false,
          error: {
            code: "PARSE_ERROR",
            message: "Error parsing request parameters",
            details: exception.message
          },
          timestamp: Time.current.iso8601
        }, status: :bad_request
      end

      def apply_filters(inventory_items)
        inventory_items = inventory_items.by_type(params[:item_type]) if params[:item_type].present?
        inventory_items = inventory_items.by_category(params[:category]) if params[:category].present?
        inventory_items = inventory_items.by_season(params[:season]) if params[:season].present?
        inventory_items = inventory_items.by_color(params[:color]) if params[:color].present?
        inventory_items = inventory_items.by_brand(params[:brand]) if params[:brand].present?
        inventory_items = inventory_items.where(status: params[:status]) if params[:status].present?

        # Special filters
        case params[:filter]
        when "recently_worn"
          inventory_items = inventory_items.recently_worn
        when "never_worn"
          inventory_items = inventory_items.never_worn
        when "most_worn"
          inventory_items = inventory_items.most_worn
        end

        inventory_items
      end

      def serialize_inventory_item(item)
        Api::V1::InventoryItemSerializer.new(item).as_json
      end

      def render_search_error(message)
        render json: {
          success: false,
          error: {
            code: "SEARCH_ERROR",
            message: message
          },
          timestamp: Time.current.iso8601
        }, status: :bad_request
      end
    end
  end
end
