# Session-based authentication for HTML controllers
# Uses JWT tokens stored in httpOnly cookies, with fallback to session
module SessionAuthenticable
  extend ActiveSupport::Concern

  included do
    helper_method :current_user, :user_signed_in?

    # Override ExceptionHandler's handlers for HTML requests
    # These handlers take precedence because they're defined after ExceptionHandler is included
    # We check inside the handler if it's an HTML request
    rescue_from ExceptionHandler::InvalidToken, with: :handle_token_error
    rescue_from ExceptionHandler::ExpiredToken, with: :handle_token_error
    rescue_from ExceptionHandler::MissingToken, with: :handle_token_error
  end

  private

  def authenticate_user!
    # Best practice: Use JWT tokens when they exist, fallback to session only if no tokens at all
    # This ensures proper token validation while maintaining backward compatibility
    if cookies.signed[:access_token].present? || cookies.signed[:refresh_token].present?
      # Tokens exist - must validate them (try refresh if expired)
      user = get_current_user_from_jwt
      unless user
        # Tokens exist but are invalid/expired and refresh failed - clear everything
        cookies.delete(:access_token)
        cookies.delete(:refresh_token)
        session.delete(:user_id)
        redirect_to login_path, alert: "Your session has expired. Please sign in again."
        return
      end
    else
      # No tokens exist - fallback to session (for backward compatibility)
      user = get_current_user_from_session
      unless user
        redirect_to login_path, alert: "Please sign in to continue"
        return
      end
    end

    @current_user = user
    # Keep session in sync for backward compatibility
    session[:user_id] = user.id unless session[:user_id] == user.id
  end

  def current_user
    return @current_user if @current_user

    # Best practice: Use JWT tokens when they exist, fallback to session only if no tokens at all
    if cookies.signed[:access_token].present? || cookies.signed[:refresh_token].present?
      # Tokens exist - must validate them
      @current_user = get_current_user_from_jwt
      # If tokens are invalid/expired and refresh failed, clear everything
      if @current_user.nil?
        cookies.delete(:access_token)
        cookies.delete(:refresh_token)
        session.delete(:user_id)
      end
    else
      # No tokens exist - fallback to session (for backward compatibility)
      @current_user = get_current_user_from_session
    end

    @current_user
  end

  def user_signed_in?
    current_user.present?
  end

  def sign_in(user)
    session[:user_id] = user.id
    @current_user = user
  end

  def sign_out
    session.delete(:user_id)
    @current_user = nil
  end

  def get_current_user_from_jwt
    token = cookies.signed[:access_token]
    return nil unless token

    # Verify token with JWT service
    decoded_token = Auth::JsonWebToken.decode(token)
    User.find_by(id: decoded_token[:user_id])
  rescue ExceptionHandler::ExpiredToken, ExceptionHandler::InvalidToken, JWT::ExpiredSignature, JWT::DecodeError
    # Try to refresh token if expired
    refreshed_user = refresh_access_token
    if refreshed_user.nil?
      # Refresh failed - clear both cookies and session to force logout
      cookies.delete(:access_token)
      cookies.delete(:refresh_token)
      session.delete(:user_id)
      return nil
    end
    refreshed_user
  rescue ActiveRecord::RecordNotFound
    # User not found - clear session
    session.delete(:user_id)
    nil
  end

  def get_current_user_from_session
    return nil unless session[:user_id]
    User.find_by(id: session[:user_id])
  end

  def refresh_access_token
    refresh_token = cookies.signed[:refresh_token]
    return nil unless refresh_token

    # Call refresh API
    response = refresh_token_via_api(refresh_token)

    if response[:success]
      # Update cookies with new tokens
      cookies.signed[:access_token] = {
        value: response[:data][:token],
        httponly: true,
        secure: Rails.env.production?,
        same_site: :lax,
        expires: 15.minutes.from_now
      }
      cookies.signed[:refresh_token] = {
        value: response[:data][:refresh_token],
        httponly: true,
        secure: Rails.env.production?,
        same_site: :lax,
        expires: 7.days.from_now
      }

      # Get user from new token
      decoded_token = Auth::JsonWebToken.decode(response[:data][:token])
      user = User.find_by(id: decoded_token[:user_id])
      # Update session with user ID for consistency
      session[:user_id] = user.id if user
      user
    else
      # Refresh failed - clear everything
      Rails.logger.warn "Token refresh failed in SessionAuthenticable, clearing auth"
      cookies.delete(:access_token)
      cookies.delete(:refresh_token)
      session.delete(:user_id)
      nil
    end
  rescue StandardError => e
    # Refresh error - clear everything
    Rails.logger.error "Token refresh error in SessionAuthenticable: #{e.message}"
    cookies.delete(:access_token)
    cookies.delete(:refresh_token)
    session.delete(:user_id)
    nil
  end

  def refresh_token_via_api(refresh_token)
    uri = URI("#{request.base_url}/api/v1/auth/refresh")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = uri.scheme == "https"

    request_obj = Net::HTTP::Post.new(uri.path, { "Content-Type" => "application/json" })
    request_obj.body = { refresh_token: refresh_token }.to_json

    response = http.request(request_obj)
    JSON.parse(response.body, symbolize_names: true)
  rescue StandardError
    { success: false }
  end

  def handle_token_error(e)
    # Only handle for HTML requests
    # For JSON requests, let ExceptionHandler handle it (but ExceptionHandler won't catch it since we're handling it first)
    # So we need to check and either handle or let it propagate
    if request.format.html?
      # Clear cookies and session
      cookies.delete(:access_token)
      cookies.delete(:refresh_token)
      session.delete(:user_id)
      # Redirect to login
      redirect_to login_path, alert: "Your session has expired. Please sign in again."
    else
      # For JSON requests, render JSON error (ExceptionHandler won't catch it since we're handling it)
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
  end
end
