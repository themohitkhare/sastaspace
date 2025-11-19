# Routing constraint to restrict access to admin users only
# Used for Sidekiq Web UI and other admin-only routes
# Checks session (primary) or JWT tokens in cookies (fallback)
# Note: In routing constraints, request is a Rack::Request, not ActionDispatch::Request
class AdminConstraint
  def matches?(request)
    user = get_user_from_request(request)
    user&.admin? == true
  end

  private

  def get_user_from_request(request)
    # Primary: Check session (works reliably in routing constraints)
    if request.session && request.session[:user_id].present?
      user = User.find_by(id: request.session[:user_id])
      return user if user
    end

    # Fallback: Try to get user from JWT token in cookies
    # In Rack::Request, cookies are a plain Hash, so we need to manually unsign
    cookie_value = request.cookies["access_token"] || request.cookies[:access_token]
    if cookie_value.present?
      # Try to unsign the cookie manually
      access_token = unsign_cookie(cookie_value) || cookie_value
      if access_token.present?
        begin
          decoded_token = Auth::JsonWebToken.decode(access_token)
          return User.find_by(id: decoded_token[:user_id])
        rescue StandardError
          # Token invalid or expired
        end
      end
    end

    nil
  end

  def unsign_cookie(signed_value)
    # Manually unsign Rails signed cookies
    # Rails uses ActiveSupport::MessageVerifier with secret_key_base
    key_generator = ActiveSupport::KeyGenerator.new(
      Rails.application.secret_key_base,
      iterations: 1000
    )
    secret = key_generator.generate_key("signed cookie")
    verifier = ActiveSupport::MessageVerifier.new(secret, serializer: Marshal, digest: "SHA1")
    verifier.verify(signed_value)
  rescue ActiveSupport::MessageVerifier::InvalidSignature, ArgumentError
    # Cookie is not signed or invalid - return nil to try raw value
    nil
  end
end
