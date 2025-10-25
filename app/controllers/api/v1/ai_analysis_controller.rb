module Api
  module V1
    class AiAnalysisController < ApplicationController
      def index
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def analyze_image
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def get_analysis
        render json: { error: "Not implemented" }, status: :not_implemented
      end

      def destroy
        render json: { error: "Not implemented" }, status: :not_implemented
      end
    end
  end
end
