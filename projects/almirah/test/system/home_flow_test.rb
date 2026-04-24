require "application_system_test_case"

# Smoke test: home page (almirah rack) redirects to sign-in when unauthenticated.
# Sign-in page renders the Google OAuth button.
#
# These tests exercise only the unauthenticated flow — no database writes.
class HomeFlowTest < ApplicationSystemTestCase
  test "root redirects to sign-in when unauthenticated" do
    visit root_url

    # Rails Authentication concern redirects to new_session_path.
    assert_no_text "Application Error"
    assert_no_text "We're sorry, but something went wrong"
    assert_current_path new_session_path
  end

  test "sign-in page shows Continue with Google button" do
    visit new_session_path

    # Google OAuth button must POST to /auth/google (omniauth-rails_csrf_protection).
    assert_selector "form[action='/auth/google']"
    assert_text /Continue with Google/i
  end
end
