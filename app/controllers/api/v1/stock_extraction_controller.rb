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
          Rails.logger.info "Stock photo extraction request - Blob ID: #{params[:blob_id]}, User: #{current_user.id}"

          # Find image blob
          image_blob = ActiveStorage::Blob.find(params[:blob_id])

          Rails.logger.info "Found blob: #{image_blob.id}, filename: #{image_blob.filename}"

          # Get inventory_item_id if provided
          inventory_item_id = params[:inventory_item_id].present? ? params[:inventory_item_id].to_i : nil

          # Use service object to queue extraction
          service = StockPhotoExtractionService.new(
            image_blob: image_blob,
            user: current_user,
            analysis_results: params[:analysis_results],
            inventory_item_id: inventory_item_id
          )

          job_id = service.queue_extraction

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
        rescue ArgumentError => e
          # Handle validation errors from service
          error_code = case e.message
          when /gender preference/
            "GENDER_MISMATCH"
          when /Inventory item not found/
            "INVALID_INVENTORY_ITEM"
          when /Analysis results/
            "INVALID_ANALYSIS_RESULTS"
          else
            "VALIDATION_ERROR"
          end

          status_code = case error_code
          when "GENDER_MISMATCH"
            :unprocessable_entity
          when "INVALID_INVENTORY_ITEM"
            :not_found
          else
            :bad_request
          end

          Rails.logger.error "Validation error: #{e.message}"
          render json: {
            success: false,
            error: {
              code: error_code,
              message: e.message
            },
            timestamp: Time.current.iso8601
          }, status: status_code
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
