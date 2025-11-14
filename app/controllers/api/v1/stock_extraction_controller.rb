module Api
  module V1
    class StockExtractionController < BaseController
      before_action :authenticate_user!

      # POST /api/v1/stock_extraction/extract
      def extract
        # Validate required parameters
        unless params[:blob_id].present?
          return render json: {
            success: false,
            error: {
              code: "MISSING_BLOB_ID",
              message: "blob_id is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        unless params[:analysis_results].present?
          return render json: {
            success: false,
            error: {
              code: "MISSING_ANALYSIS_RESULTS",
              message: "analysis_results is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        begin
          # Debug logging
          Rails.logger.info "Stock photo extraction request - Blob ID: #{params[:blob_id]}, User: #{current_user.id}, Item ID from analysis: #{params[:analysis_results][:name] rescue 'unknown'}"

          # Find image blob
          image_blob = ActiveStorage::Blob.find(params[:blob_id])

          Rails.logger.info "Found blob: #{image_blob.id}, filename: #{image_blob.filename}"

          # Parse analysis results - convert ActionController::Parameters to Hash if needed
          # Permit only the fields used by ExtractionPromptBuilder and validation
          analysis_results = if params[:analysis_results].is_a?(ActionController::Parameters)
            params[:analysis_results].permit(
              :name, :description, :category_name, :category_matched, :subcategory,
              :material, :style, :style_notes,
              :brand_matched, :brand_name, :brand_suggestion,
              :gender_appropriate, :confidence, :extraction_prompt,
              colors: [] # Array of strings
            ).to_h
          elsif params[:analysis_results].is_a?(Hash)
            # Filter to only allowed keys for security
            permitted_keys = %w[
              name description category_name category_matched subcategory
              material style style_notes
              brand_matched brand_name brand_suggestion
              gender_appropriate confidence extraction_prompt colors
            ]
            params[:analysis_results].slice(*permitted_keys)
          else
            parsed = JSON.parse(params[:analysis_results])
            if parsed.is_a?(Hash)
              permitted_keys = %w[
                name description category_name category_matched subcategory
                material style style_notes
                brand_matched brand_name brand_suggestion
                gender_appropriate confidence extraction_prompt colors
              ]
              parsed.slice(*permitted_keys)
            else
              parsed
            end
          end

          # Validate gender appropriateness
          if analysis_results["gender_appropriate"] == false
            return render json: {
              success: false,
              error: {
                code: "GENDER_MISMATCH",
                message: "This item does not match your gender preference"
              },
              timestamp: Time.current.iso8601
            }, status: :unprocessable_entity
          end

          # Generate unique job ID
          job_id = SecureRandom.uuid

          # Get inventory_item_id if provided (for precise item lookup when multiple items share the same blob)
          inventory_item_id = params[:inventory_item_id].present? ? params[:inventory_item_id].to_i : nil

          # Validate inventory_item_id belongs to current_user if provided
          if inventory_item_id.present?
            item = current_user.inventory_items.find_by(id: inventory_item_id)
            unless item
              return render json: {
                success: false,
                error: {
                  code: "INVALID_INVENTORY_ITEM",
                  message: "Inventory item not found or does not belong to you"
                },
                timestamp: Time.current.iso8601
              }, status: :not_found
            end
            Rails.logger.info "Using provided inventory_item_id: #{inventory_item_id} for blob #{image_blob.id}"
          end

          # Queue extraction job
          ExtractStockPhotoJob.perform_later(
            image_blob.id,
            analysis_results,
            current_user.id,
            job_id,
            inventory_item_id  # Pass inventory_item_id to job for precise lookup
          )

          Rails.logger.info "Stock photo extraction job queued. Blob ID: #{image_blob.id}, Inventory Item ID: #{inventory_item_id || 'auto-detect'}, Job ID: #{job_id}, User: #{current_user.id}"

          render json: {
            success: true,
            data: {
              job_id: job_id,
              blob_id: image_blob.id,
              status: "processing",
              estimated_time: "30-60 seconds"
            },
            message: "Stock photo extraction started",
            timestamp: Time.current.iso8601
          }, status: :accepted
        rescue ActiveRecord::RecordNotFound => e
          Rails.logger.error "Blob not found: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "BLOB_NOT_FOUND",
              message: "Image blob not found"
            },
            timestamp: Time.current.iso8601
          }, status: :not_found
        rescue JSON::ParserError => e
          Rails.logger.error "Invalid JSON in analysis_results: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "INVALID_ANALYSIS_RESULTS",
              message: "analysis_results must be valid JSON"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        rescue StandardError => e
          Rails.logger.error "Error starting stock photo extraction: #{e.message}"
          Rails.logger.error e.backtrace.first(10).join("\n")
          render json: {
            success: false,
            error: {
              code: "EXTRACTION_ERROR",
              message: "Failed to start stock photo extraction: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end

      # GET /api/v1/stock_extraction/status/:job_id
      def status
        job_id = params[:job_id]

        unless job_id.present?
          return render json: {
            success: false,
            error: {
              code: "MISSING_JOB_ID",
              message: "job_id is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end

        begin
          status_data = ExtractStockPhotoJob.get_status(job_id)

          render json: {
            success: true,
            data: status_data,
            timestamp: Time.current.iso8601
          }
        rescue StandardError => e
          Rails.logger.error "Error retrieving extraction status: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "STATUS_ERROR",
              message: "Failed to retrieve extraction status: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end
    end
  end
end
