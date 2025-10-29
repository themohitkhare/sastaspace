# Session-based authentication for HTML controllers
# Uses JWT tokens stored in httpOnly cookies, with fallback to session
module SessionAuthenticable
  extend ActiveSupport::Concern

  included do
    helper_method :current_user, :user_signed_in?
  end

  private

  def authenticate_user!
    user = get_current_user_from_jwt || get_current_user_from_session

    unless user
      redirect_to login_path, alert: "Please sign in to continue"
      return
    end

    @current_user = user
    # Keep session in sync for backward compatibility
    session[:user_id] = user.id unless session[:user_id] == user.id
  end

  def current_user
    @current_user ||= get_current_user_from_jwt || get_current_user_from_session
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
  rescue JWT::ExpiredSignature, JWT::DecodeError
    # Try to refresh token if expired
    refresh_access_token
  rescue ActiveRecord::RecordNotFound
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
      User.find_by(id: decoded_token[:user_id])
    else
      nil
    end
  rescue StandardError
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
end
