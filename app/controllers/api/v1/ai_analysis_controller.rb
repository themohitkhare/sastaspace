module Api
  module V1
    class AiAnalysisController < ApplicationController
      include Authenticable

      before_action :authenticate_user!
      before_action :set_inventory_item, only: [ :analyze_image, :get_analysis, :destroy ]
      before_action :set_ai_analysis, only: [ :get_analysis, :destroy ]

      # POST /api/v1/inventory_items/:id/analyze
      # POST /api/v1/ai/analyze
      def analyze_image
        # Queue analysis job
        AnalyzeClothingImageJob.perform_later(@inventory_item.id)

        render json: {
          success: true,
          data: {
            inventory_item_id: @inventory_item.id,
            status: "analysis_queued"
          },
          message: "Analysis job queued successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/inventory_items/:id/analysis
      # GET /api/v1/ai/analysis/:id
      def get_analysis
        render json: {
          success: true,
          data: {
            analysis: serialize_analysis(@ai_analysis)
          },
          message: "Analysis retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # GET /api/v1/ai/analyses
      def index
        analyses = AiAnalysis
                     .where(user: current_user)
                     .includes(:inventory_item, :user)
                     .order(created_at: :desc)
                     .page(params[:page])
                     .per(params[:per_page] || 20)

        render json: {
          success: true,
          data: {
            analyses: analyses.map { |analysis| serialize_analysis(analysis) },
            pagination: {
              current_page: analyses.current_page,
              total_pages: analyses.total_pages,
              total_count: analyses.total_count,
              per_page: analyses.limit_value
            }
          },
          message: "Analyses retrieved successfully",
          timestamp: Time.current.iso8601
        }
      end

      # DELETE /api/v1/inventory_items/:id/analysis
      def destroy
        @ai_analysis.destroy!

        render json: {
          success: true,
          message: "Analysis deleted successfully",
          timestamp: Time.current.iso8601
        }
      end

      private

      def set_inventory_item
        if params[:id].present?
          @inventory_item = current_user.inventory_items.find(params[:id])
        elsif params[:inventory_item_id].present?
          @inventory_item = current_user.inventory_items.find(params[:inventory_item_id])
        else
          render json: {
            success: false,
            error: {
              code: "INVENTORY_ITEM_NOT_FOUND",
              message: "Inventory item ID is required"
            },
            timestamp: Time.current.iso8601
          }, status: :bad_request
        end
      rescue ActiveRecord::RecordNotFound
        render json: {
          success: false,
          error: {
            code: "INVENTORY_ITEM_NOT_FOUND",
            message: "Inventory item not found"
          },
          timestamp: Time.current.iso8601
        }, status: :not_found
      end

      def set_ai_analysis
        if params[:id].present?
          # If ID is provided directly, it's the analysis ID
          @ai_analysis = AiAnalysis.joins(:inventory_item)
                                  .where(id: params[:id], inventory_items: { user_id: current_user.id })
                                  .first
        else
          # Otherwise, get the latest analysis for the inventory item
          @ai_analysis = @inventory_item.ai_analyses.order(created_at: :desc).first
        end

        unless @ai_analysis
          render json: {
            success: false,
            error: {
              code: "ANALYSIS_NOT_FOUND",
              message: "Analysis not found"
            },
            timestamp: Time.current.iso8601
          }, status: :not_found
        end
      end

      def serialize_analysis(analysis)
        {
          id: analysis.id,
          inventory_item_id: analysis.inventory_item_id,
          analysis_type: analysis.analysis_type,
          analysis_data: analysis.analysis_data,
          confidence_score: analysis.confidence_score,
          model_used: analysis.model_used,
          processing_time_ms: analysis.processing_time_ms,
          high_confidence: analysis.high_confidence,
          created_at: analysis.created_at.iso8601,
          updated_at: analysis.updated_at.iso8601,
          inventory_item: {
            id: analysis.inventory_item.id,
            name: analysis.inventory_item.name,
            item_type: analysis.inventory_item.item_type
          }
        }
      end
    end
  end
end
