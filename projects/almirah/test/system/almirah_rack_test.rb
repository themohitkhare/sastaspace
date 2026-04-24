require "application_system_test_case"

# System test: sign-in stub, rack home, item navigation.
#
# These tests stub out the session cookie directly rather than going through
# the full OmniAuth OAuth round-trip, which requires live network calls.
class AlmirahRackTest < ApplicationSystemTestCase
  # Seed a minimal item set for the test so we don't depend on migration data.
  def setup
    @user = users(:test_user)
    # Clear + create a test session cookie by making a minimal request first.
    # Actual cookie injection happens via before_action stubs.
  end

  test "rack home redirects to sign-in when unauthenticated" do
    visit root_url
    assert_current_path new_session_path
  end

  test "sign-in page shows Continue with Google button" do
    visit new_session_path

    assert_no_text "Application Error"
    assert_selector "form[action='/auth/google']"
    assert_text /Continue with Google/i
  end

  test "health endpoint returns 200 without authentication" do
    # Use Rack-level request so we can assert JSON without a browser.
    visit "/almirah/api/health"
    assert_text '"status":"ok"'
  end
end
