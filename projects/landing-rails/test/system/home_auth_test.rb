# frozen_string_literal: true

require "application_system_test_case"

# home_auth_test.rb
#
# Verifies the home page renders correctly for authenticated users.
# Uses OmniAuth test mode to stub the Google callback without a real OAuth round-trip.
class HomeAuthTest < ApplicationSystemTestCase
  teardown do
    sign_out_omniauth
  end

  test "sign-out button is visible on home when signed in via Google" do
    sign_in_as_google(email: "testuser@example.com")
    visit root_url

    # The hero section must show the sign-out form (button_to DELETE /session)
    assert_selector "form[action='#{session_path}']"
    assert_selector "button", text: /sign out/i
  end

  test "sign-in link is not visible when signed in" do
    sign_in_as_google(email: "testuser@example.com")
    visit root_url

    # "Sign in with Google" link should NOT appear when already authenticated
    assert_no_selector "a", text: /sign in with google/i
  end

  test "signed-in user email is shown on home page" do
    email = sign_in_as_google(email: "testuser@example.com")
    visit root_url

    assert_text email
  end
end
