module Api
  module V1
    class ClothingDetectionController < BaseController
      before_action :authenticate_user!

      # POST /api/v1/clothing_detection/analyze
      # Analyzes an image to detect multiple clothing items
      def analyze
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

        max_size = 10.megabytes # Allow larger images for multi-item detection
        if image.size > max_size
          return render json: {
            success: false,
            error: {
              code: "IMAGE_TOO_LARGE",
              message: "Image must be less than 10MB"
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

          # Queue background job for clothing detection
          job = ClothingDetectionJob.perform_later(
            blob.id,
            current_user.id,
            model_name: params[:model_name] || "qwen3-vl:8b"
          )

          # Return immediately with job ID for tracking
          render json: {
            success: true,
            data: {
              job_id: job.job_id,
              blob_id: blob.id,
              user_id: current_user.id,
              status: "processing",
              message: "Clothing detection job queued successfully"
            },
            timestamp: Time.current.iso8601
          }, status: :accepted
        rescue ArgumentError => e
          Rails.logger.error "Invalid arguments for clothing detection: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "INVALID_REQUEST",
              message: e.message
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        rescue StandardError => e
          Rails.logger.error "Error during clothing detection: #{e.message}"
          Rails.logger.error e.backtrace.first(10).join("\n")
          render json: {
            success: false,
            error: {
              code: "DETECTION_ERROR",
              message: "Failed to analyze image: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end

      # GET /api/v1/clothing_detection/analysis/:id
      # Retrieve a specific clothing analysis by ID
      def show
        analysis = ClothingAnalysis.find_by(id: params[:id], user: current_user)

        unless analysis
          return render json: {
            success: false,
            error: {
              code: "NOT_FOUND",
              message: "Analysis not found"
            },
            timestamp: Time.current.iso8601
          }, status: :not_found
        end

        render json: {
          success: true,
          data: {
            analysis: {
              id: analysis.id,
              blob_id: analysis.image_blob_id,
              total_items_detected: analysis.items_detected,
              people_count: analysis.people_count,
              items: analysis.items,
              confidence: analysis.confidence,
              status: analysis.status,
              created_at: analysis.created_at,
              updated_at: analysis.updated_at
            }
          },
          message: "Analysis retrieved successfully",
          timestamp: Time.current.iso8601
        }, status: :ok
      end

      # GET /api/v1/clothing_detection/status/:job_id
      # Check the status of a clothing detection job
      def status
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

        begin
          status_data = ClothingDetectionJob.get_status(job_id)

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
          when "processing", "scheduled", "retrying"
            render json: {
              success: true,
              data: {
                job_id: job_id,
                status: status_data["status"],
                message: status_data["data"] || "Job is processing"
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
                message: status_data["error"]&.dig("message") || "Job not found or expired"
              },
              timestamp: Time.current.iso8601
            }, status: :not_found
          end
        rescue StandardError => e
          Rails.logger.error "Error retrieving detection status: #{e.message}"
          render json: {
            success: false,
            error: {
              code: "STATUS_ERROR",
              message: "Failed to retrieve job status: #{e.message}"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        end
      end

      # GET /api/v1/clothing_detection/analyses
      # List all clothing analyses for the current user
      def index
        analyses = current_user.clothing_analyses
                              .order(created_at: :desc)
                              .page(params[:page])
                              .per(params[:per_page] || 20)

        render json: {
          success: true,
          data: {
            analyses: analyses.map do |analysis|
              {
                id: analysis.id,
                blob_id: analysis.image_blob_id,
                total_items_detected: analysis.items_detected,
                people_count: analysis.people_count,
                confidence: analysis.confidence,
                status: analysis.status,
                created_at: analysis.created_at,
                updated_at: analysis.updated_at
              }
            end,
            pagination: {
              current_page: analyses.current_page,
              total_pages: analyses.total_pages,
              total_count: analyses.total_count,
              per_page: analyses.limit_value
            }
          },
          message: "Analyses retrieved successfully",
          timestamp: Time.current.iso8601
        }, status: :ok
      end
    end
  end
end
