# Authentication concern for JWT-based auth
module Authenticable
  extend ActiveSupport::Concern

  # Module-level variable for test environment token blacklist
  @test_blacklisted_tokens = []

  included do
    before_action :authenticate_user!
  end

  private

  def authenticate_user!
    token = request.headers['Authorization']&.split(' ')&.last
    raise ExceptionHandler::MissingToken, 'Token is missing' unless token

    # Check if token is blacklisted
    # In test environment, use a simple module variable since cache is disabled
    if Rails.env.test?
      if Authenticable.instance_variable_get(:@test_blacklisted_tokens)&.include?(token)
        raise ExceptionHandler::InvalidToken, 'Token has been revoked'
      end
    else
      if Rails.cache.read("blacklisted_token_#{token}")
        raise ExceptionHandler::InvalidToken, 'Token has been revoked'
      end
    end

    decoded_token = Auth::JsonWebToken.decode(token)
    @current_user = User.find(decoded_token[:user_id])
  rescue ActiveRecord::RecordNotFound => e
    render json: {
      success: false,
      error: {
        code: 'AUTHENTICATION_ERROR',
        message: 'Invalid token',
        details: e.message
      },
      timestamp: Time.current.iso8601
    }, status: :unauthorized
  end

  def current_user
    @current_user
  end

  def user_signed_in?
    @current_user.present?
  end

  def authenticate_user_optional
    token = request.headers['Authorization']&.split(' ')&.last
    return unless token

    # Check if token is blacklisted
    if Rails.env.test?
      if Authenticable.instance_variable_get(:@test_blacklisted_tokens)&.include?(token)
        return
      end
    else
      if Rails.cache.read("blacklisted_token_#{token}")
        return
      end
    end

    begin
      decoded_token = Auth::JsonWebToken.decode(token)
      @current_user = User.find(decoded_token[:user_id])
    rescue ActiveRecord::RecordNotFound, JWT::DecodeError, JWT::ExpiredSignature
      # Silently ignore authentication errors for optional auth
      @current_user = nil
    end
  end
end
