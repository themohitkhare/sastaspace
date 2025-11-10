# Mission Control - Jobs configuration
# Restricts access to admin users only
# This lambda is called for each request to the Mission Control dashboard
MissionControl::Jobs::Engine.config.authentication = lambda do |request|
  # Get current user from session/cookies (using existing authentication)
  user = nil

  # Try to get user from JWT token in cookies (signed cookies)
  access_token = request.cookies.signed[:access_token] || request.cookies[:access_token]
  if access_token.present?
    begin
      decoded_token = Auth::JsonWebToken.decode(access_token)
      user = User.find_by(id: decoded_token[:user_id])
    rescue StandardError => e
      Rails.logger.debug "Mission Control auth: JWT decode failed - #{e.message}"
      # Token invalid or expired, try session
    end
  end

  # Fallback to session
  if user.nil? && request.session[:user_id].present?
    user = User.find_by(id: request.session[:user_id])
  end

  # Only allow admin users - return false to deny access
  unless user&.admin?
    Rails.logger.warn "Mission Control access denied for user: #{user&.id || 'anonymous'}"
    false
  else
    true
  end
end
