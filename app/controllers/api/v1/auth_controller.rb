module Api
  module V1
    class AuthController < ApplicationController
      def register
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def login
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def refresh
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def me
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def logout
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def logout_all
        render json: { error: "Not implemented" }, status: :not_implemented
      end
    end
  end
end
