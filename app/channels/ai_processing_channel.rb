class AiProcessingChannel < ApplicationCable::Channel
  def subscribed
    # Subscribe to detection updates for the user
    if params[:user_id].present?
      stream_from "detection_#{params[:user_id]}"
      Rails.logger.info "Subscribed to detection updates for user #{params[:user_id]}"
    end

    # Subscribe to stock photo extraction updates for the user
    if params[:user_id].present?
      stream_from "stock_extraction_#{params[:user_id]}"
      Rails.logger.info "Subscribed to stock extraction updates for user #{params[:user_id]}"
    end

    # Subscribe to extraction updates for a specific analysis
    if params[:analysis_id].present?
      stream_from "extraction_#{params[:analysis_id]}"
      Rails.logger.info "Subscribed to extraction updates for analysis #{params[:analysis_id]}"
    end

    # If no params, reject the subscription
    unless params[:user_id].present? || params[:analysis_id].present?
      reject
    end
  end

  def unsubscribed
    # Cleanup when client disconnects
    Rails.logger.info "Client unsubscribed from AI processing channel"
  end
end
