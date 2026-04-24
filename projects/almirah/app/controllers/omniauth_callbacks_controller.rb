class OmniauthCallbacksController < ApplicationController
  allow_unauthenticated_access

  # POST /auth/google/callback
  # Google redirects here after the user grants consent.
  # We find-or-create the user by email and start a new session.
  def google_oauth2
    auth = request.env["omniauth.auth"]
    email = auth.info.email

    user = User.find_or_initialize_by(email_address: email.strip.downcase)

    is_admin = admin_email?(email)

    if user.new_record?
      # Google-auth users have no password; generate a random one.
      # They authenticate exclusively via Google OAuth going forward.
      user.password = SecureRandom.hex(32)
      user.name     = auth.info.name
      user.provider = "google"
      user.uid      = auth.uid
      user.admin    = is_admin
      user.save!
    else
      # Update provider/uid and sync admin flag with public.admins allowlist.
      attrs = {}
      attrs[:provider] = "google" if user.uid.blank?
      attrs[:uid]      = auth.uid  if user.uid.blank?
      attrs[:admin]    = is_admin  if user.admin? != is_admin
      user.update_columns(**attrs) if attrs.any?
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

  private

  # Check public.admins allowlist table (not a Rails-managed table).
  def admin_email?(email)
    result = ActiveRecord::Base.connection.execute(
      ActiveRecord::Base.sanitize_sql_array(
        ["SELECT 1 FROM public.admins WHERE email = ? LIMIT 1", email.strip.downcase]
      )
    )
    result.any?
  rescue ActiveRecord::StatementInvalid
    # public.admins may not exist in dev/test — treat as not admin.
    false
  end
end
