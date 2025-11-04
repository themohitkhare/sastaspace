module Api
  module V1
    class DocsController < BaseController
      skip_before_action :authenticate_user!
      def show
        # Simple OpenAPI spec stub
        render json: {
          openapi: "3.0.0",
          info: {
            title: "SastaSpace API",
            version: "1.0.0"
          },
          paths: {}
        }, status: :ok
      end

      def openapi
        show
      end
    end
  end
end
