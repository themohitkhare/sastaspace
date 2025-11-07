# Standardized API response formatting
# Provides helper methods for consistent JSON responses across all API endpoints
module ApiResponse
  extend ActiveSupport::Concern

  private

  # Render a successful response
  # @param data [Hash, ActiveRecord::Base, Array] The data to return
  # @param message [String] Optional success message
  # @param status [Symbol] HTTP status code (default: :ok)
  def render_success(data: nil, message: nil, status: :ok)
    response_data = {
      success: true,
      timestamp: Time.current.iso8601,
      request_id: current_request_id
    }

    # Add data if provided
    response_data[:data] = data if data.present?

    # Add message if provided
    response_data[:message] = message if message.present?

    render json: response_data, status: status
  end

  # Render a created response (for POST requests)
  # @param data [Hash, ActiveRecord::Base] The created resource
  # @param message [String] Optional success message
  def render_created(data: nil, message: nil)
    render_success(data: data, message: message, status: :created)
  end

  # Render a paginated response
  # @param collection [Kaminari::PaginatableArray] Paginated collection
  # @param serializer [Proc, Symbol] Optional serializer block or method name
  # @param message [String] Optional success message
  def render_paginated(collection:, serializer: nil, message: nil)
    # Serialize items if serializer provided
    items = if serializer.is_a?(Proc)
              collection.map(&serializer)
    elsif serializer.is_a?(Symbol) && respond_to?(serializer, true)
              collection.map { |item| send(serializer, item) }
    else
              collection
    end

    pagination_data = {
      items: items,
      pagination: {
        current_page: collection.current_page,
        total_pages: collection.total_pages,
        total_count: collection.total_count,
        per_page: collection.limit_value,
        has_next_page: collection.current_page < collection.total_pages,
        has_prev_page: collection.current_page > 1
      }
    }

    render_success(data: pagination_data, message: message)
  end

  # Render an error response
  # @param code [String] Error code (e.g., "VALIDATION_ERROR")
  # @param message [String] Error message
  # @param details [Hash, String] Optional error details
  # @param status [Symbol] HTTP status code (default: :bad_request)
  def render_error_response(code:, message:, details: nil, status: :bad_request)
    response_data = {
      success: false,
      error: {
        code: code,
        message: message,
        timestamp: Time.current.iso8601,
        request_id: current_request_id
      }
    }

    # Add details if provided
    response_data[:error][:details] = details if details.present?

    render json: response_data, status: status
  end

  # Render validation errors
  # @param errors [ActiveModel::Errors] Model errors object
  # @param message [String] Optional custom message
  def render_validation_errors(errors, message: nil)
    render_error_response(
      code: "VALIDATION_ERROR",
      message: message || "Validation failed",
      details: errors.as_json,
      status: :unprocessable_entity
    )
  end

  # Get current request ID for responses
  def current_request_id
    return nil unless respond_to?(:request) && request
    request.env["REQUEST_ID"]
  end
end
