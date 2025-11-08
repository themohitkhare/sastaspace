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
    # Try to get token from Authorization header first
    token = request.headers["Authorization"]&.split(" ")&.last

    # If no token in header, try to get from cookies (for web-based API calls)
    token ||= cookies.signed[:access_token]

    # If no access token but we have a refresh token, try to refresh
    if token.blank? && cookies.signed[:refresh_token].present?
      if refresh_access_token_from_cookies
        token = cookies.signed[:access_token]
      end
    end

    raise ExceptionHandler::MissingToken, "Token is missing" unless token

    # Check if token is blacklisted
    # In test environment, use a simple module variable since cache is disabled
    if Rails.env.test?
      if Authenticable.instance_variable_get(:@test_blacklisted_tokens)&.include?(token)
        raise ExceptionHandler::InvalidToken, "Token has been revoked"
      end
    else
      if Rails.cache.read("blacklisted_token_#{token}")
        raise ExceptionHandler::InvalidToken, "Token has been revoked"
      end
    end

    decoded_token = Auth::JsonWebToken.decode(token)
    @current_user = User.find(decoded_token[:user_id])
  rescue ExceptionHandler::ExpiredToken, JWT::ExpiredSignature, JWT::DecodeError => e
    # If token is expired and we're using cookies, try to refresh
    if cookies.signed[:refresh_token].present? && refresh_access_token_from_cookies
      retry
    else
      # If refresh failed, clear cookies and return unauthorized
      cookies.delete(:access_token)
      cookies.delete(:refresh_token)
      render json: {
        success: false,
        error: {
          code: "AUTHENTICATION_ERROR",
          message: "Invalid or expired token. Please log in again.",
          details: e.message
        },
        timestamp: Time.current.iso8601
      }, status: :unauthorized
    end
  rescue ActiveRecord::RecordNotFound => e
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

  def refresh_access_token_from_cookies
    refresh_token = cookies.signed[:refresh_token]
    return false unless refresh_token

    begin
      uri = URI("#{request.base_url}/api/v1/auth/refresh")
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == "https"
      http.open_timeout = 2
      http.read_timeout = 2

      request_obj = Net::HTTP::Post.new(uri.path, { "Content-Type" => "application/json" })
      request_obj.body = { refresh_token: refresh_token }.to_json

      response = http.request(request_obj)
      result = JSON.parse(response.body, symbolize_names: true)

      if result[:success] && result[:data] && result[:data][:token]
        # Update cookies with new tokens
        cookies.signed[:access_token] = {
          value: result[:data][:token],
          httponly: true,
          secure: Rails.env.production?,
          same_site: :lax,
          expires: 15.minutes.from_now
        }
        if result[:data][:refresh_token]
          cookies.signed[:refresh_token] = {
            value: result[:data][:refresh_token],
            httponly: true,
            secure: Rails.env.production?,
            same_site: :lax,
            expires: 7.days.from_now
          }
        end
        true
      else
        # Refresh failed - clear cookies to force re-login
        Rails.logger.warn "Token refresh failed, clearing auth cookies"
        cookies.delete(:access_token)
        cookies.delete(:refresh_token)
        false
      end
    rescue StandardError => e
      # Refresh failed - clear cookies to force re-login
      Rails.logger.error "Token refresh error: #{e.message}"
      cookies.delete(:access_token)
      cookies.delete(:refresh_token)
      false
    end
  end

  def current_user
    @current_user
  end

  def user_signed_in?
    @current_user.present?
  end

  def authenticate_user_optional
    token = request.headers["Authorization"]&.split(" ")&.last
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
