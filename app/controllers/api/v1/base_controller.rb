module Api
  module V1
    class BaseController < ActionController::API
      # Include cookie support for API controllers (needed for Authenticable concern)
      include ActionController::Cookies

      # Include concerns
      include Authenticable  # Authentication required by default (secure by default)
      include StructuredLogging
      include AuditLogging   # Security audit logging
      include ErrorHandling  # Comprehensive error handling (must come before ExceptionHandler)
      include ExceptionHandler  # Authentication-specific error handling (checked after ErrorHandling)
      include ApiResponse    # Standardized response formatting
      include HttpCaching   # HTTP caching support (ETag, Last-Modified)
      include RateLimiting   # Rate limiting support (complements middleware)

      # Add request ID to all responses
      before_action :set_request_id_header
      before_action :log_request_start
      before_action :validate_request_size
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

      # Validate request size to prevent DoS attacks
      def validate_request_size
        max_size = 10.megabytes # 10MB max request size
        if request.content_length && request.content_length > max_size
          render_error_response(
            code: "REQUEST_TOO_LARGE",
            message: "Request body is too large. Maximum size is 10MB.",
            status: :payload_too_large
          )
        end
      end
    end
  end
end
