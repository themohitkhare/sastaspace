# Comprehensive error handling for API controllers
# Provides standardized error responses and handles common exceptions
module ErrorHandling
  extend ActiveSupport::Concern

  included do
    # Order matters: Rails evaluates rescue_from in reverse order (bottom to top)
    # So we define StandardError FIRST, then more specific handlers override it

    # Handle general application errors (catch-all for unexpected errors)
    rescue_from StandardError, with: :handle_standard_error

    # Handle ActiveRecord validation errors (more specific, overrides StandardError)
    rescue_from ActiveRecord::RecordInvalid, with: :handle_record_invalid
    rescue_from ActiveRecord::RecordNotFound, with: :handle_record_not_found

    # Handle parameter parsing errors (more specific, overrides StandardError)
    rescue_from ActionController::ParameterMissing, with: :handle_parameter_missing
    rescue_from ActionDispatch::Http::Parameters::ParseError, with: :handle_parse_error

    # Note: Authentication errors are handled by ExceptionHandler concern
    # We don't duplicate them here to avoid conflicts
  end

  private

  # Handle ActiveRecord validation errors
  def handle_record_invalid(exception)
    log_error("Validation failed", { errors: exception.record.errors.as_json })
    render_error(
      code: "VALIDATION_ERROR",
      message: "Validation failed",
      details: exception.record.errors.as_json,
      status: :unprocessable_entity
    )
  end

  # Handle record not found errors
  def handle_record_not_found(exception)
    # ActiveRecord::RecordNotFound can be raised manually or from find
    # When raised manually, model and id may not be available
    details = {}
    model_name = nil

    begin
      if exception.respond_to?(:model)
        model = exception.model
        if model.present?
          details[:model] = model
          model_name = model
        end
      end
    rescue NoMethodError
      # model method might not work for manually raised exceptions
    end

    begin
      if exception.respond_to?(:id)
        id = exception.id
        details[:id] = id if id.present?
      end
    rescue NoMethodError
      # id method might not work for manually raised exceptions
    end

    # Always ensure we have a message in details
    if details.empty?
      details[:message] = exception.message.presence || "Resource not found"
    end

    # Create a user-friendly message
    # Convert model name to readable format (e.g., "InventoryItem" -> "Inventory item")
    if model_name.present?
      friendly_model = model_name.to_s.underscore.humanize.downcase
      message = "#{friendly_model.capitalize} not found"
    else
      # Use exception message if no model, otherwise use default
      message = exception.message.presence || "Resource not found"
    end

    log_error("Record not found", details)
    render_error(
      code: "NOT_FOUND",
      message: message,
      details: details,
      status: :not_found
    )
  end

  # Handle missing parameter errors
  def handle_parameter_missing(exception)
    log_error("Missing parameter", { param: exception.param })
    render_error(
      code: "BAD_REQUEST",
      message: "Missing required parameter",
      details: { param: exception.param },
      status: :bad_request
    )
  end

  # Handle JSON parse errors
  def handle_parse_error(exception)
    log_error("JSON parse error", { error: exception.message })
    render_error(
      code: "BAD_REQUEST",
      message: "Invalid JSON format",
      details: { error: exception.message },
      status: :bad_request
    )
  end

  # Handle general application errors
  # Excludes authentication exceptions and ActiveRecord exceptions which are handled separately
  def handle_standard_error(exception)
    # Skip exceptions that are handled by specific handlers
    # Re-raise them so the specific handlers can catch them
    # Note: ActiveRecord exceptions are already handled by their own rescue_from,
    # so they won't reach this handler unless explicitly re-raised
    if exception.is_a?(ExceptionHandler::InvalidToken) ||
       exception.is_a?(ExceptionHandler::MissingToken) ||
       exception.is_a?(ExceptionHandler::ExpiredToken)
      raise exception
    end

    # Log full error details for debugging
    log_error("Unhandled error", {
      error: exception.class.name,
      message: exception.message,
      backtrace: Rails.env.development? ? exception.backtrace.first(5) : nil
    })

    # In production, don't expose internal error details
    message = Rails.env.production? ? "An internal error occurred" : exception.message

    render_error(
      code: "INTERNAL_ERROR",
      message: message,
      details: Rails.env.development? ? { backtrace: exception.backtrace.first(5) } : nil,
      status: :internal_server_error
    )
  end

  # Standardized error response renderer
  def render_error(code:, message:, details: nil, status:)
    response_data = {
      success: false,
      error: {
        code: code,
        message: message
      },
      timestamp: Time.current.iso8601,
      request_id: current_request_id
    }

    # Add details if provided (include even if empty hash to maintain consistent structure)
    response_data[:error][:details] = details unless details.nil?

    render json: response_data, status: status
  end

  # Get current request ID for error responses
  def current_request_id
    return nil unless respond_to?(:request) && request
    request.env["REQUEST_ID"]
  end
end
