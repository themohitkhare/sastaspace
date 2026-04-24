# OmniAuth — Google OAuth2 strategy.
#
# Single OAuth client for all apps on sastaspace.com. The redirect URI is
# always https://sastaspace.com/auth/google/callback (landing owns it).
# Other apps receive the session cookie after the user is redirected back.
#
# omniauth-rails_csrf_protection makes GET-initiated OAuth flows safe by
# requiring a POST to /auth/google before the redirect.

OmniAuth.config.logger = Rails.logger

# Silence the OmniAuth 2.x "request phase path" warning — POST is our intent.
OmniAuth.config.silence_get_warning = true

Rails.application.config.middleware.use OmniAuth::Builder do
  provider :google_oauth2,
    ENV.fetch("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID_NOT_SET"),
    ENV.fetch("GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET_NOT_SET"),
    {
      scope: "email,profile",
      prompt: "select_account",
      access_type: "offline",
      # image_aspect_ratio: "square",
      # image_size: 50,
    }
end
