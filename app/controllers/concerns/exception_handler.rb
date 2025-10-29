# Exception handling for authentication
module ExceptionHandler
  extend ActiveSupport::Concern

  included do
    rescue_from ExceptionHandler::InvalidToken, with: :invalid_token
    rescue_from ExceptionHandler::MissingToken, with: :missing_token
    rescue_from ExceptionHandler::ExpiredToken, with: :expired_token
  end

  private

  def invalid_token(e)
    render json: {
      success: false,
      error: {
        code: "AUTHENTICATION_ERROR",
        message: "Invalid token",
        details: e.message
      },
      timestamp: Time.current.iso8601
    }, status: :unauthorized
  end

  def missing_token(e)
    render json: {
      success: false,
      error: {
        code: "AUTHENTICATION_ERROR",
        message: "Missing token",
        details: e.message
      },
      timestamp: Time.current.iso8601
    }, status: :unauthorized
  end

  def expired_token(e)
    render json: {
      success: false,
      error: {
        code: "AUTHENTICATION_ERROR",
        message: "Invalid token",
        details: e.message
      },
      timestamp: Time.current.iso8601
    }, status: :unauthorized
  end

  class InvalidToken < StandardError; end
  class MissingToken < StandardError; end
  class ExpiredToken < StandardError; end
end
