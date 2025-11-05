module Api
  module V1
    class BaseController < ActionController::API
      # Include cookie support for API controllers (needed for Authenticable concern)
      include ActionController::Cookies

      # Include concerns
      include Authenticable  # Authentication required by default (secure by default)
      include StructuredLogging
      include ExceptionHandler

      # Add request ID to all responses
      before_action :set_request_id_header

      private

      def set_request_id_header
        response.headers["X-Request-ID"] = request.env["REQUEST_ID"]
      end
    end
  end
end
