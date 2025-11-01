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
        # Extract inventory_item_ids before building (not a direct model attribute)
        inventory_item_ids = params[:outfit]&.dig(:inventory_item_ids) || params[:outfit]&.dig("inventory_item_ids") || []
        inventory_item_ids = Array(inventory_item_ids).map(&:to_i).reject(&:zero?)

        outfit = current_user.outfits.new(outfit_params.except(:inventory_item_ids))

        if outfit.save
          # Create outfit items if inventory_item_ids provided
          if inventory_item_ids.any?
            inventory_item_ids.each_with_index do |item_id, index|
              # Verify item belongs to current user
              inventory_item = current_user.inventory_items.find_by(id: item_id)
              if inventory_item
                outfit.outfit_items.create!(
                  inventory_item: inventory_item,
                  position: index
                )
              else
                Rails.logger.warn "Skipping inventory_item_id #{item_id} - not found or doesn't belong to user"
              end
            end
            outfit.reload # Reload to include associations
          end

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

      # GET /api/v1/outfits/color_analysis
      # Analyze color coordination for a set of items (for outfit builder)
      def color_analysis
        item_ids = params[:item_ids] || []
        item_ids = Array(item_ids).map(&:to_i).reject(&:zero?)

        unless item_ids.any?
          return render json: {
            success: false,
            error: {
              code: "INVALID_PARAMS",
              message: "Item IDs are required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        # Fetch items that belong to current user
        items = current_user.inventory_items
                          .includes(:category, :ai_analyses)
                          .where(id: item_ids)
                          .to_a

        unless items.length == item_ids.length
          return render json: {
            success: false,
            error: {
              code: "INVALID_ITEMS",
              message: "Some items not found or don't belong to you"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        # Analyze color coordination
        analysis = ColorCoordinationService.analyze(items)

        render json: {
          success: true,
          data: analysis,
          message: "Color analysis completed",
          timestamp: Time.current.iso8601
        }
      rescue StandardError => e
        Rails.logger.error "Error in color analysis: #{e.message}"
        Rails.logger.error e.backtrace.first(10).join("\n")
        render json: {
          success: false,
          error: {
            code: "ANALYSIS_ERROR",
            message: "Failed to analyze colors: #{e.message}"
          },
          timestamp: Time.current.iso8601
        }, status: :internal_server_error
      end

      def suggestions
        authorize_owner!

        limit = params[:limit]&.to_i || 6
        exclude_ids = params[:exclude_ids] || []

        # Get outfit items
        outfit_items = @outfit.inventory_items.includes(:category, :brand, :tags, primary_image_attachment: :blob)

        # Get AI-powered suggestions using VectorSearchService
        suggested_items = VectorSearchService.suggest_outfit_items(
          current_user,
          outfit_items,
          limit: limit,
          exclude_ids: exclude_ids.map(&:to_i)
        )

        # Serialize suggested items using the serializer
        suggested_data = suggested_items.map { |item| Api::V1::InventoryItemSerializer.new(item).as_json }

        render json: {
          success: true,
          data: {
            items: suggested_data,
            outfit_id: @outfit.id,
            existing_items_count: outfit_items.count,
            suggestions_count: suggested_items.count
          },
          message: "AI suggestions generated successfully",
          timestamp: Time.current.iso8601
        }
      rescue ActiveRecord::RecordNotFound
        raise # Let it bubble up to be handled by authorize_owner!
      rescue StandardError => e
        Rails.logger.error "Error generating outfit suggestions: #{e.message}"
        Rails.logger.error e.backtrace.first(10).join("\n")
        render json: {
          success: false,
          error: {
            code: "SUGGESTIONS_ERROR",
            message: "Failed to generate suggestions: #{e.message}"
          },
          timestamp: Time.current.iso8601
        }, status: :internal_server_error
      end

      def duplicate
        authorize_owner!
        dup_attrs = @outfit.attributes.slice("name", "description", "season", "occasion")
        dup = current_user.outfits.create!(dup_attrs.merge("name" => "#{@outfit.name} (Copy)"))
        # Items copy will be implemented when outfit_items schema is aligned
        render json: { success: true, data: { outfit: serialize(dup) }, message: "Duplicated", timestamp: Time.current }, status: :created
      end

      # POST /api/v1/outfits/analyze_photo
      # Accepts an outfit photo upload and starts AI analysis in background
      def analyze_photo
        unless params[:image].present?
          return render json: {
            success: false,
            error: {
              code: "MISSING_IMAGE",
              message: "Image file is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        # Validate image
        image = params[:image]
        allowed_types = %w[image/jpeg image/jpg image/png image/webp]

        unless allowed_types.include?(image.content_type)
          return render json: {
            success: false,
            error: {
              code: "INVALID_IMAGE_TYPE",
              message: "Image must be JPEG, PNG, or WebP"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        max_size = 5.megabytes
        if image.size > max_size
          return render json: {
            success: false,
            error: {
              code: "IMAGE_TOO_LARGE",
              message: "Image must be less than 5MB"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        begin
          # Create or reuse an existing ActiveStorage blob for the image (deduplication)
          blob = Services::BlobDeduplicationService.find_or_create_blob(
            io: image.open,
            filename: image.original_filename,
            content_type: image.content_type
          )

          # Generate unique job ID
          job_id = SecureRandom.uuid

          # Queue background job
          AnalyzeOutfitPhotoJob.perform_later(blob.id, current_user.id, job_id)

          Rails.logger.info "Outfit photo upload initiated. Blob ID: #{blob.id}, Job ID: #{job_id}, User: #{current_user.id}"

          render json: {
            success: true,
            data: {
              job_id: job_id,
              blob_id: blob.id, # Include blob ID so frontend can use it later
              status: "processing",
              message: "Outfit photo analysis started"
            },
            timestamp: Time.current.iso8601
          }, status: :accepted
        rescue StandardError => e
          Rails.logger.error "Error starting outfit photo analysis: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "ANALYSIS_ERROR",
              message: "Failed to start outfit photo analysis: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end

      # GET /api/v1/outfits/analyze_photo_status/:job_id
      # Poll for outfit photo analysis job status and results
      def analyze_photo_status
        job_id = params[:job_id]

        unless job_id.present?
          return render json: {
            success: false,
            error: {
              code: "MISSING_JOB_ID",
              message: "Job ID is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        status_data = AnalyzeOutfitPhotoJob.get_status(job_id)

        case status_data["status"]
        when "completed"
          render json: {
            success: true,
            data: {
              job_id: job_id,
              status: "completed",
              analysis: status_data["data"]
            },
            timestamp: Time.current.iso8601
          }
        when "processing"
          render json: {
            success: true,
            data: {
              job_id: job_id,
              status: "processing"
            },
            timestamp: Time.current.iso8601
          }
        when "failed"
          render json: {
            success: false,
            data: {
              job_id: job_id,
              status: "failed",
              error: status_data["error"]
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        else
          render json: {
            success: false,
            error: {
              code: "JOB_NOT_FOUND",
              message: status_data["error"] || "Job not found or expired"
            },
            timestamp: Time.current.iso8601
          }, status: :not_found
        end
      end

      private

      def set_outfit
        @outfit = Outfit.find(params[:id])
      end

      def authorize_owner!
        raise ActiveRecord::RecordNotFound unless @outfit.user_id == current_user&.id
      end

      def outfit_params
        params.require(:outfit).permit(:name, :description, :is_favorite, :formality, :season, :occasion, inventory_item_ids: [])
      end

      def serialize(outfit_or_collection)
        if outfit_or_collection.respond_to?(:map)
          outfit_or_collection.map { |o| serialize_one(o) }
        else
          serialize_one(outfit_or_collection)
        end
      end

      def serialize_one(o)
        # Load items with associations if not already loaded
        items = o.respond_to?(:inventory_items) ? o.inventory_items.includes(:category, :brand, primary_image_attachment: :blob) : []

        data = {
          id: o.id,
          name: o.name,
          description: o.description,
          is_favorite: o.is_favorite,
          season: (o.respond_to?(:season) ? o.season : nil),
          occasion: o.occasion,
          wear_count: (o.respond_to?(:wear_count) ? o.wear_count : nil),
          last_worn_at: (o.respond_to?(:last_worn_at) ? o.last_worn_at : nil),
          items: items.map { |item|
            {
              id: item.id,
              name: item.name,
              category: item.category&.name,
              primary_image_url: item.primary_image.attached? ? Rails.application.routes.url_helpers.url_for(item.primary_image) : nil
            }
          }
        }
        data
      end
    end
  end
end
