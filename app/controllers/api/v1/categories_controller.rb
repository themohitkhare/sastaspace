module Api
  module V1
    class CategoriesController < ApplicationController
      include Authenticable

      skip_before_action :authenticate_user!, only: [ :index, :show, :tree, :roots, :children ]
      before_action :set_category, only: [ :show, :children, :inventory_items ]
      before_action :authenticate_user_optional, only: [ :index, :show, :tree, :roots, :children ]

      # GET /api/v1/categories
      def index
        @categories = Category.active.ordered.includes(:parent_category, :subcategories)
        @categories = @categories.root_categories if params[:roots_only] == "true"

        render json: {
          success: true,
          data: {
            categories: serialize_categories(@categories)
          },
          message: "Categories retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/categories/:id
      def show
        render json: {
          success: true,
          data: {
            category: serialize_category(@category)
          },
          message: "Category retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/categories/tree
      def tree
        @categories = Category.active.includes(:subcategories).root_categories

        render json: {
          success: true,
          data: {
            categories: serialize_category_tree(@categories)
          },
          message: "Category tree retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/categories/roots
      def roots
        @categories = Category.active.root_categories.ordered

        render json: {
          success: true,
          data: {
            categories: serialize_categories(@categories)
          },
          message: "Root categories retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/categories/:id/children
      def children
        @children = @category.subcategories.active.ordered

        render json: {
          success: true,
          data: {
            category: serialize_category(@category),
            children: serialize_categories(@children)
          },
          message: "Category children retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/categories/:id/inventory_items
      def inventory_items
        return render_authentication_required unless user_signed_in?

        # Include items from subcategories if requested
        categories = params[:include_subcategories] == "true" ?
          [ @category ] + @category.descendants : [ @category ]

        @items = current_user.inventory_items
                            .where(category: categories)
                            .includes(:category, :brand, :tags,
                                      primary_image_attachment: :blob,
                                      additional_images_attachments: :blob)
                            .page(params[:page])
                            .per(params[:per_page] || 20)

        render json: {
          success: true,
          data: {
            category: serialize_category(@category),
            inventory_items: @items.map { |item| serialize_inventory_item(item) },
            pagination: {
              current_page: @items.current_page,
              total_pages: @items.total_pages,
              total_count: @items.total_count,
              per_page: @items.limit_value
            },
            include_subcategories: params[:include_subcategories] == "true"
          },
          message: "Category inventory items retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      private

      def set_category
        @category = Category.find(params[:id])
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "NOT_FOUND",
            message: "Category not found"
          },
          timestamp: Time.current.iso8601
        }, status: :not_found
      end

      def serialize_categories(categories)
        Api::V1::CategorySerializer.serialize_collection(
          categories,
          { include_item_count: true, user: user_signed_in? ? current_user : nil }
        )
      end

      def serialize_category(category)
        Api::V1::CategorySerializer.new(
          category,
          { include_item_count: true, user: user_signed_in? ? current_user : nil }
        ).as_json
      end

      def serialize_category_tree(categories)
        Api::V1::CategorySerializer.serialize_tree(
          categories,
          { include_item_count: true, user: user_signed_in? ? current_user : nil }
        )
      end

      def serialize_inventory_item(item)
        Api::V1::InventoryItemSerializer.new(item).as_json
      end

      def render_authentication_required
        render json: {
          success: false,
          error: {
            code: "AUTHENTICATION_REQUIRED",
            message: "Authentication required to access inventory items"
          },
          timestamp: Time.current.iso8601
        }, status: :unauthorized
      end
    end
  end
end
