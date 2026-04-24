class OmniauthCallbacksController < ApplicationController
  allow_unauthenticated_access

  # POST /auth/google/callback
  # Google redirects here after the user grants consent.
  # We find-or-create the user by email and start a new session.
  def google_oauth2
    auth = request.env["omniauth.auth"]
    email = auth.info.email

    user = User.find_or_initialize_by(email_address: email.strip.downcase)

    if user.new_record?
      # Google-auth users have no password; generate a random one.
      # They authenticate exclusively via Google OAuth going forward.
      user.password = SecureRandom.hex(32)
      user.name     = auth.info.name
      user.provider = "google"
      user.uid      = auth.uid
      user.save!
    else
      # Update provider/uid in case the user previously had a different flow.
      user.update_columns(provider: "google", uid: auth.uid) if user.uid.blank?
    end

    start_new_session_for(user)
    redirect_to after_authentication_url, notice: "Signed in as #{user.email_address}"
  rescue => e
    Rails.logger.error "[OmniAuth] Google callback error: #{e.message}"
    redirect_to new_session_path, alert: "Google sign-in failed. Please try again."
  end

  # Failure callback — OmniAuth redirects here on error.
  def failure
    redirect_to new_session_path, alert: "Google sign-in was cancelled or failed."
  end
end
