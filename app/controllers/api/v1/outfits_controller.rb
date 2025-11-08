module Api
  module V1
    class OutfitsController < BaseController
      skip_before_action :authenticate_user!, only: [ :index, :show ]
      before_action :authenticate_user_optional, only: [ :index, :show ]
      before_action :parse_json_params, only: [ :create, :update ]
      before_action :set_outfit, only: [ :show, :update, :destroy, :wear, :favorite, :suggestions, :duplicate, :completeness ]

      def index
        outfits = current_user ? current_user.outfits : Outfit.none
        # Check if request is fresh (304 Not Modified)
        base_relation = current_user ? current_user.outfits : Outfit.none
        return if set_cache_headers(base_relation)
        render json: { success: true, data: { outfits: serialize(outfits) }, message: "OK", timestamp: Time.current }
      end

      def show
        authorize_owner!
        # Check if request is fresh (304 Not Modified)
        return if set_cache_headers(@outfit)
        render json: { success: true, data: { outfit: serialize(@outfit) }, message: "OK", timestamp: Time.current }
      end

      def create
        # Extract inventory_item_ids before building (not a direct model attribute)
        # Handle both Hash and String params (from JSON requests)
        outfit_data = params[:outfit]
        if outfit_data.is_a?(String)
          outfit_data = JSON.parse(outfit_data) rescue {}
        end
        outfit_data = outfit_data.with_indifferent_access if outfit_data.is_a?(Hash)

        inventory_item_ids = outfit_data[:inventory_item_ids] || outfit_data["inventory_item_ids"] || []
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
        # Track outfit wearing across all items
        @outfit.outfit_items.each do |outfit_item|
          outfit_item.increment!(:worn_count)
          outfit_item.update!(last_worn_at: Time.current)

          # Also update individual inventory item wear count
          if outfit_item.inventory_item.respond_to?(:wear_count)
            outfit_item.inventory_item.increment!(:wear_count)
            outfit_item.inventory_item.update!(last_worn_at: Time.current) if outfit_item.inventory_item.respond_to?(:last_worn_at=)
          end
        end

        render json: {
          success: true,
          data: {
            outfit: serialize(@outfit),
            worn_count: @outfit.worn_count
          },
          message: "Outfit wear tracked",
          timestamp: Time.current
        }
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
        exclude_ids = Array(params[:exclude_ids]).map(&:to_i).reject(&:zero?)

        # Get outfit items
        outfit_items = @outfit.inventory_items.includes(:category, :brand, :tags, primary_image_attachment: :blob)

        Rails.logger.info "Generating suggestions for outfit #{@outfit.id} with #{outfit_items.count} items, excluding #{exclude_ids.length} IDs"

        # If outfit has no items, return empty suggestions
        if outfit_items.empty?
          Rails.logger.info "Outfit has no items, returning empty suggestions"
          return render json: {
            success: true,
            data: {
              items: [],
              outfit_id: @outfit.id,
              existing_items_count: 0,
              suggestions_count: 0
            },
            message: "Add items to your outfit to see AI suggestions",
            timestamp: Time.current.iso8601
          }
        end

        # Get AI-powered suggestions using VectorSearchService
        suggested_items = VectorSearchService.suggest_outfit_items(
          current_user,
          outfit_items,
          limit: limit,
          exclude_ids: exclude_ids
        )

        Rails.logger.info "Found #{suggested_items.count} suggestions for outfit #{@outfit.id}"

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
          message: suggested_items.any? ? "AI suggestions generated successfully" : "No suggestions available. Try adding more items to your wardrobe.",
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

      def completeness
        authorize_owner!
        analysis = {
          score: @outfit.completeness_score,
          complete: @outfit.complete?,
          missing_categories: missing_categories,
          suggestions: outfit_suggestions
        }

        render json: { success: true, data: analysis, message: "Completeness analysis", timestamp: Time.current }
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

        # Validate file signature (magic bytes) to prevent malicious file uploads
        unless FileSignatureValidator.valid?(image, image.content_type)
          return render json: {
            success: false,
            error: {
              code: "INVALID_FILE_SIGNATURE",
              message: "File signature does not match declared type. File may be corrupted or malicious."
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

      def parse_json_params
        if request.content_type == "application/json"
          request.body.rewind
          body_content = request.body.read

          # Parse JSON body if it exists
          if body_content.present?
            begin
              json_params = JSON.parse(body_content)
              params.merge!(json_params)
            rescue JSON::ParserError
              # If JSON parsing fails, continue with existing params
            end
          end

          # Also handle case where params[:outfit] might be a JSON string
          if params[:outfit].is_a?(String)
            begin
              parsed_outfit = JSON.parse(params[:outfit])
              params[:outfit] = parsed_outfit
            rescue JSON::ParserError
              # If parsing fails, leave as is
            end
          end
        end
      rescue StandardError => e
        # If anything goes wrong, continue with existing params
        Rails.logger.warn "Error parsing JSON params: #{e.message}"
      end

      def set_outfit
        @outfit = Outfit.find(params[:id])
      end

      def authorize_owner!
        raise ActiveRecord::RecordNotFound unless @outfit.user_id == current_user&.id
      end

      def outfit_params
        # Ensure params[:outfit] is a Hash (parse_json_params should handle this, but be defensive)
        outfit_param = params[:outfit]
        if outfit_param.is_a?(String)
          outfit_param = JSON.parse(outfit_param) rescue {}
          params[:outfit] = outfit_param
        end

        params.require(:outfit).permit(
          :name, :description, :is_favorite, :formality, :season, :occasion, :status,
          inventory_item_ids: [],
          metadata: [ :weather, :formality_level, :color_scheme, :style_notes, :created_for_date ]
        )
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
          status: (o.respond_to?(:status) ? o.status : nil),
          metadata: (o.respond_to?(:metadata) ? o.metadata : nil),
          wear_count: o.worn_count,
          last_worn_at: o.last_worn_at,
          completeness_score: (o.respond_to?(:completeness_score) ? o.completeness_score : nil),
          complete: (o.respond_to?(:complete?) ? o.complete? : nil),
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

      def missing_categories
        missing = []
        missing << "clothing" unless @outfit.has_clothing_item?
        missing << "shoes" unless @outfit.has_shoes?
        missing << "accessories" unless @outfit.has_accessories?
        missing
      end

      def outfit_suggestions
        # Future: AI-powered suggestions based on existing items
        []
      end
    end
  end
end
