require "test_helper"

# Base class for Capybara system tests.
#
# Uses headless Chrome via selenium-webdriver. Capybara drives the full browser
# stack so Turbo, Stimulus, and import-map-loaded JS all run as in production.
#
# To run:
#   bin/rails test:system
class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  driven_by :selenium, using: :headless_chrome, screen_size: [ 1400, 900 ] do |options|
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
  end

  # Helper: sign in a user via stubbed OmniAuth Google callback.
  #
  # Sets OmniAuth test mode and mocks the google_oauth2 auth hash.
  # Returns the email used so callers can assert against it.
  #
  # Usage:
  #   sign_in_as_google(email: "user@example.com")
  #   visit root_url
  #   assert_text "user@example.com"
  def sign_in_as_google(email:, name: "Test User", uid: "test-uid-#{SecureRandom.hex(4)}")
    OmniAuth.config.test_mode = true
    OmniAuth.config.mock_auth[:google_oauth2] = OmniAuth::AuthHash.new(
      provider: "google",
      uid: uid,
      info: { email: email, name: name }
    )
    # Drive the browser to the callback URL — OmniAuth in test mode
    # fires the callback action directly without a real Google round-trip.
    visit "/auth/google/callback"
    email
  end

  def sign_out_omniauth
    OmniAuth.config.test_mode = false
    OmniAuth.config.mock_auth.delete(:google_oauth2)
  end
end
