module Api
  module V1
    class DocsController < ApplicationController
      def show
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def openapi
        render json: { error: "Not implemented" }, status: :not_implemented
      end
    end
  end
end
