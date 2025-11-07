module Api
  module V1
    class BaseController < ActionController::API
      # Include cookie support for API controllers (needed for Authenticable concern)
      include ActionController::Cookies

      # Include concerns
      include Authenticable  # Authentication required by default (secure by default)
      include StructuredLogging
      include ErrorHandling  # Comprehensive error handling (must come before ExceptionHandler)
      include ExceptionHandler  # Authentication-specific error handling (checked after ErrorHandling)
      include ApiResponse    # Standardized response formatting

      # Add request ID to all responses
      before_action :set_request_id_header
      before_action :log_request_start
      after_action :log_request_complete

      private

      def set_request_id_header
        response.headers["X-Request-ID"] = request.env["REQUEST_ID"]
      end

      def log_request_start
        log_info("API request started", {
          method: request.method,
          path: request.path,
          params: sanitize_params(params.to_unsafe_h)
        })
      end

      def log_request_complete
        log_info("API request completed", {
          method: request.method,
          path: request.path,
          status: response.status,
          duration_ms: calculate_request_duration
        })
      end

      def calculate_request_duration
        return nil unless request.env["REQUEST_START_TIME"]
        ((Time.current - request.env["REQUEST_START_TIME"]) * 1000).round(2)
      end
    end
  end
end
