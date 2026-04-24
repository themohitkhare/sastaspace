require "application_system_test_case"

# Smoke test: home page renders with 200 and the sign-in button is present.
#
# This test does NOT require a database connection — it exercises only the
# unauthenticated home page and the sign-in link.
class HomeFlowTest < ApplicationSystemTestCase
  test "root renders 200 with sign-in link when not authenticated" do
    visit root_url

    # Page should load without error.
    assert_no_text "Application Error"
    assert_no_text "We're sorry, but something went wrong"

    # Sign-in link or button must be present.
    assert_selector "a[href='#{new_session_path}']", text: /sign in/i
  end

  test "sign-in page shows Continue with Google button" do
    visit new_session_path

    # Google OAuth button should be present and POST to /auth/google.
    assert_selector "form[action='/auth/google']", text: /Continue with Google/i
  end
end
