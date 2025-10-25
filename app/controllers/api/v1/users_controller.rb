module Api
  module V1
    class UsersController < ApplicationController
      def export
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def export_status
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def download_export
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def delete
        render json: { error: "Not implemented" }, status: :not_implemented
      end
    end
  end
end
