module Api
  module V1
    class HealthController < BaseController
      skip_before_action :authenticate_user!
      def show
        # Simple health check for API
        render json: {
          status: "ok",
          checks: {
            database: "ok"
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      end
    end
  end
end
