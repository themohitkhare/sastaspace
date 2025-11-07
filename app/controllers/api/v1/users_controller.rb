module Api
  module V1
    class UsersController < BaseController
      # Export and delete endpoints require authentication
      before_action :authenticate_user!

      # POST /api/v1/users/export
      # Initiates GDPR data export for the current user
      def export
        # Queue background job to generate export
        job_id = SecureRandom.uuid
        ExportUserDataJob.perform_later(current_user.id, job_id)

        log_info("GDPR data export initiated", { user_id: current_user.id, job_id: job_id })

        render json: {
          success: true,
          data: {
            job_id: job_id,
            status: "processing",
            message: "Data export has been initiated. Use the status endpoint to check progress."
          },
          timestamp: Time.current.iso8601
        }, status: :accepted
      end

      # GET /api/v1/users/export/status
      # Checks the status of a data export job
      def export_status
        job_id = params[:job_id]

        unless job_id.present?
          return render_error_response(
            code: "MISSING_JOB_ID",
            message: "Job ID is required",
            status: :bad_request
          )
        end

        # Check job status (stored in cache or database)
        status_data = ExportUserDataJob.get_status(job_id, current_user.id)

        case status_data["status"]
        when "completed"
          render json: {
            success: true,
            data: {
              job_id: job_id,
              status: "completed",
              download_url: status_data["download_url"],
              expires_at: status_data["expires_at"]
            },
            timestamp: Time.current.iso8601
          }
        when "processing"
          render json: {
            success: true,
            data: {
              job_id: job_id,
              status: "processing",
              message: "Export is still being generated"
            },
            timestamp: Time.current.iso8601
          }
        when "failed"
          render json: {
            success: false,
            error: {
              code: "EXPORT_FAILED",
              message: status_data["error"] || "Export generation failed"
            },
            timestamp: Time.current.iso8601
          }, status: :internal_server_error
        else
          render_error_response(
            code: "JOB_NOT_FOUND",
            message: "Export job not found or expired",
            status: :not_found
          )
        end
      end

      # GET /api/v1/users/export/download
      # Downloads the exported user data
      def download_export
        job_id = params[:job_id]

        unless job_id.present?
          return render_error_response(
            code: "MISSING_JOB_ID",
            message: "Job ID is required",
            status: :bad_request
          )
        end

        status_data = ExportUserDataJob.get_status(job_id, current_user.id)

        unless status_data["status"] == "completed" && status_data["file_path"]
          return render_error_response(
            code: "EXPORT_NOT_READY",
            message: "Export is not ready for download",
            status: :not_found
          )
        end

        # Verify file exists and belongs to user
        file_path = status_data["file_path"]

        # Security: Validate file path to prevent directory traversal
        # Ensure file path is within export directory and contains user ID
        export_dir = ExportUserDataJob::EXPORT_DIR.to_s

        # Validate file_path is a string and starts with export directory
        unless file_path.is_a?(String) && file_path.start_with?(export_dir) && file_path.include?("user_#{current_user.id}_")
          return render_error_response(
            code: "EXPORT_NOT_FOUND",
            message: "Export file not found",
            status: :not_found
          )
        end

        # Additional security: Normalize path and verify it's still within export directory
        # This prevents directory traversal attacks (e.g., ../../../etc/passwd)
        begin
          normalized_path = File.expand_path(file_path, export_dir)
          expanded_export_dir = File.expand_path(export_dir)
          unless normalized_path.start_with?(expanded_export_dir)
            return render_error_response(
              code: "EXPORT_NOT_FOUND",
              message: "Export file not found",
              status: :not_found
            )
          end
        rescue StandardError
          return render_error_response(
            code: "EXPORT_NOT_FOUND",
            message: "Export file not found",
            status: :not_found
          )
        end

        unless File.exist?(normalized_path)
          return render_error_response(
            code: "EXPORT_NOT_FOUND",
            message: "Export file not found",
            status: :not_found
          )
        end

        # Log export download
        log_info("GDPR data export downloaded", { user_id: current_user.id, job_id: job_id })

        # Security: Use sanitized filename (constructed from validated current_user.id, not user input)
        # File path is validated above to be within export directory and normalized
        safe_filename = "sastaspace_export_#{current_user.id}_#{Time.current.to_i}.json"
        send_file normalized_path,
                  filename: safe_filename,
                  type: "application/json",
                  disposition: "attachment"
      end

      # DELETE /api/v1/users/delete
      # Implements GDPR "Right to be Forgotten" - permanently deletes user account and all data
      def delete
        # Double confirmation - require password or confirmation token
        unless params[:confirmation].present? || params[:password].present?
          return render_error_response(
            code: "CONFIRMATION_REQUIRED",
            message: "Account deletion requires confirmation. Please provide your password or confirmation token.",
            status: :bad_request
          )
        end

        # Verify password if provided
        if params[:password].present?
          unless current_user.authenticate(params[:password])
            return render_error_response(
              code: "INVALID_PASSWORD",
              message: "Invalid password. Account deletion cancelled.",
              status: :unauthorized
            )
          end
        end

        user_id = current_user.id
        user_email = current_user.email

        # Queue background job to delete all user data
        DeleteUserDataJob.perform_later(user_id)

        # Log deletion request (before user is deleted)
        log_info("GDPR account deletion initiated", { user_id: user_id, email: user_email })

        # Sign out immediately
        token = request.headers["Authorization"]&.split(" ")&.last
        if token
          Rails.cache.write("blacklisted_token_#{token}", true, expires_in: 15.minutes)
        end
        current_user.invalidate_all_refresh_tokens!

        render json: {
          success: true,
          data: {
            message: "Account deletion has been initiated. All your data will be permanently deleted within 30 days."
          },
          timestamp: Time.current.iso8601
        }, status: :accepted
      end
    end
  end
end
