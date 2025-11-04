module Api
  module V1
    class InventoryItemsController < BaseController

      before_action :authenticate_user!
      before_action :set_inventory_item, only: [ :show, :update, :destroy, :worn, :similar, :attach_primary_image, :attach_additional_images, :detach_primary_image, :detach_additional_image ]

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
        # Extract blob_id before building - it's not a model attribute
        blob_id_param = params[:inventory_item]&.dig(:blob_id)

        # Build item without blob_id (it's not a model attribute)
        item_params = inventory_item_params.except(:blob_id)
        @inventory_item = current_user.inventory_items.build(item_params)

        # Normalize category/subcategory if needed
        if @inventory_item.category_id.present?
          selected = Category.find_by(id: @inventory_item.category_id)
          if selected&.parent_id.present?
            @inventory_item.subcategory_id = selected.id
            node = selected
            node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
            @inventory_item.category_id = node&.id || selected.id
          end
        end

        if @inventory_item.save
          # Handle blob_id from AI upload if present
          if blob_id_param.present?
            begin
              # Convert to integer to ensure proper lookup
              blob_id = blob_id_param.to_i
              blob = ActiveStorage::Blob.find_by(id: blob_id)

              if blob
                # Explicitly create attachment with correct name to ensure it's "primary_image" not "attachments"
                @inventory_item.primary_image_attachment&.purge # Remove existing if any
                @inventory_item.primary_image.attach(blob)

                # Note: ActiveStorage attachments are persisted automatically when attach() is called
                # No need to explicitly save as attach() creates the attachment record directly

                Rails.logger.info "Successfully attached blob #{blob.id} as primary image for inventory item #{@inventory_item.id}"

                # Reload to ensure attachment is available for serialization
                @inventory_item.reload

                # Verify attachment was created correctly
                attachment = @inventory_item.primary_image_attachment
                if attachment && attachment.persisted?
                  Rails.logger.info "Attachment verified: name=#{attachment.name}, blob_id=#{attachment.blob_id}, record=#{attachment.record_type}##{attachment.record_id}"
                else
                  Rails.logger.error "Attachment not found or not persisted after attach! Item ID: #{@inventory_item.id}, Blob ID: #{blob.id}"
                end
              else
                Rails.logger.warn "Blob #{blob_id} not found in database"
              end
            rescue ActiveRecord::RecordNotFound => e
              Rails.logger.warn "Blob #{blob_id} not found: #{e.message}"
            rescue StandardError => e
              Rails.logger.error "Error attaching blob to inventory item: #{e.message}"
              Rails.logger.error e.backtrace.first(5).join("\n")
              # Continue anyway - item creation succeeded, just image attachment failed
            end
          end

          begin
            serialized_item = serialize_inventory_item(@inventory_item)
            render json: {
              success: true,
              data: {
                inventory_item: serialized_item
              },
              message: "Inventory item created successfully",
              timestamp: Time.current.iso8601
            }, status: :created
          rescue StandardError => e
            Rails.logger.error "Error serializing inventory item: #{e.message}"
            Rails.logger.error e.backtrace.first(10).join("\n")
            # Return item without serialization error details, but log it
            render json: {
              success: false,
              error: {
                code: "SERIALIZATION_ERROR",
                message: "Item created but failed to serialize: #{e.message}"
              },
              timestamp: Time.current.iso8601
            }, status: :internal_server_error
          end
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

      # POST /api/v1/inventory_items/batch_create
      # Accepts array of item data from outfit analysis and creates multiple items atomically
      def batch_create
        items_array = params[:items] || params["items"]

        unless items_array.is_a?(Array) && items_array.present?
          return render json: {
            success: false,
            error: {
              code: "INVALID_PARAMS",
              message: "Items array is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        created_items = []
        errors = []

        # Use transaction to ensure atomicity
        ActiveRecord::Base.transaction do
          items_array.each_with_index do |item_data, index|
            begin
              # Convert to ActionController::Parameters if needed
              # Handle both symbol and string keys from JSON
              if item_data.is_a?(ActionController::Parameters)
                item_params_hash = item_data
              else
                # Convert hash with symbol keys to string keys for Parameters
                normalized_data = item_data.stringify_keys
                item_params_hash = ActionController::Parameters.new(normalized_data)
              end

              # Extract blob_id if present (from outfit photo analysis) BEFORE permitting
              blob_id = item_params_hash[:blob_id] || item_params_hash["blob_id"]

              # Extract category_id before permitting (in case it gets lost)
              category_id = (item_params_hash[:category_id] || item_params_hash["category_id"]).to_i if (item_params_hash[:category_id] || item_params_hash["category_id"]).present?

              # Build item params - permit nested structure
              item_params = item_params_hash.permit(
                :name, :description, :category_id, :brand_id, :status,
                metadata: {}, tag_ids: []
              )

              # Ensure category_id is set as integer (permit might convert to string or lose it)
              item_params[:category_id] = category_id if category_id.present?

              # Build and normalize category
              item = current_user.inventory_items.build(item_params)

              if item.category_id.present?
                selected = Category.find_by(id: item.category_id)
                if selected&.parent_id.present?
                  item.subcategory_id = selected.id
                  node = selected
                  node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
                  item.category_id = node&.id || selected.id
                end
              end

              if item.save
                # Handle blob attachment if provided
                if blob_id.present?
                  begin
                    blob = ActiveStorage::Blob.find_by(id: blob_id.to_i)
                    if blob
                      item.primary_image.attach(blob)
                      item.reload
                      Rails.logger.info "Attached blob #{blob.id} to batch-created item #{item.id}"
                    end
                  rescue StandardError => e
                    Rails.logger.warn "Failed to attach blob to item at index #{index}: #{e.message}"
                    # Continue - item created, just image attachment failed
                  end
                end

                created_items << item
              else
                errors << {
                  index: index,
                  errors: item.errors.full_messages
                }
              end
            rescue StandardError => e
              Rails.logger.error "Error creating item at index #{index}: #{e.message}"
              errors << {
                index: index,
                errors: [ e.message ]
              }
            end
          end

          # If any errors, rollback transaction
          if errors.any?
            raise ActiveRecord::Rollback
          end
        end

        if errors.any?
          render json: {
            success: false,
            error: {
              code: "BATCH_CREATE_ERROR",
              message: "Some items failed to create",
              details: errors
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        else
          render json: {
            success: true,
            data: {
              inventory_items: created_items.map { |item| serialize_inventory_item(item) },
              count: created_items.length
            },
            message: "Successfully created #{created_items.length} item(s)",
            timestamp: Time.current.iso8601
          }, status: :created
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
        # Support both file upload and blob_id
        if params[:image].present?
          # Use deduplication for new image uploads
          blob = Services::BlobDeduplicationService.find_or_create_blob(
            io: params[:image].open,
            filename: params[:image].original_filename,
            content_type: params[:image].content_type
          )
          @inventory_item.primary_image_attachment&.purge # Remove existing if any
          @inventory_item.primary_image.attach(blob)
          render json: {
            success: true,
            data: {
              image_url: url_for(@inventory_item.primary_image)
            },
            message: "Primary image attached successfully",
            timestamp: Time.current.iso8601
          }
        elsif params[:blob_id].present?
          begin
            blob = ActiveStorage::Blob.find_by(id: params[:blob_id])

            if blob
              # Explicitly create attachment with correct name
              @inventory_item.primary_image_attachment&.purge # Remove existing if any
              @inventory_item.primary_image.attach(blob)
              @inventory_item.reload

              # Verify attachment was created correctly
              attachment = @inventory_item.primary_image_attachment
              unless attachment && attachment.name == "primary_image"
                Rails.logger.error "Attachment created with wrong name! Expected 'primary_image', got '#{attachment&.name}'"
              end

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
                  code: "BLOB_NOT_FOUND",
                  message: "Blob not found"
                },
                timestamp: Time.current.iso8601
              }, status: :not_found
            end
          rescue ActiveRecord::RecordNotFound
            render json: {
              success: false,
              error: {
                code: "BLOB_NOT_FOUND",
                message: "Blob not found"
              },
              timestamp: Time.current.iso8601
            }, status: :not_found
          end
        else
          render json: {
            success: false,
            error: {
              code: "MISSING_IMAGE",
              message: "Image file or blob_id is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end
      end

      # POST /api/v1/inventory_items/:id/additional_images
      def attach_additional_images
        if params[:images].present?
          # Use deduplication for additional image uploads
          Array(params[:images]).each do |image|
            blob = Services::BlobDeduplicationService.find_or_create_blob(
              io: image.open,
              filename: image.original_filename,
              content_type: image.content_type
            )
            @inventory_item.additional_images.attach(blob)
          end
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

      # POST /api/v1/inventory_items/analyze_image_for_creation
      # Accepts an image upload and starts AI analysis in background
      def analyze_image_for_creation
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
          AnalyzeImageForCreationJob.perform_later(blob.id, current_user.id, job_id)

          # Store blob_id in session as fallback (in case form submission fails to include it)
          session[:pending_blob_id] = blob.id.to_s

          Rails.logger.info "Image upload initiated. Blob ID: #{blob.id}, Job ID: #{job_id}, User: #{current_user.id}"

          render json: {
            success: true,
            data: {
              job_id: job_id,
              blob_id: blob.id, # Include blob ID so frontend can attach it later
              status: "processing",
              message: "Image analysis started"
            },
            timestamp: Time.current.iso8601
          }, status: :accepted
        rescue StandardError => e
          Rails.logger.error "Error starting image analysis: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "ANALYSIS_ERROR",
              message: "Failed to start image analysis: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end

      # GET /api/v1/inventory_items/analyze_image_status/:job_id
      # Poll for analysis job status and results
      def analyze_image_status
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

        status_data = AnalyzeImageForCreationJob.get_status(job_id)

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
            :purchase_price, :purchase_date, :primary_image, :blob_id, additional_images: [],
            metadata: {}, # Allow any metadata hash structure
            tag_ids: []
          )
          # Note: blob_id is permitted here so we can extract it, but it's removed
          # before building the model since it's not a model attribute
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
