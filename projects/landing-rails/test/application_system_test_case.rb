require "test_helper"

# Base class for Capybara system tests.
#
# Uses headless Chrome via selenium-webdriver. Capybara drives the full browser
# stack so Turbo, Stimulus, and import-map-loaded JS all run as in production.
#
# System tests run serially (no parallelization) to avoid port-conflict issues
# with the Capybara-managed Puma server and shared-DB connection races.
#
# To run:
#   bundle exec ruby -Itest test/system/home_unauth_test.rb
class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  # System tests must NOT use transactional fixtures — Capybara's Puma server
  # runs in a separate thread and cannot see uncommitted transactions from the
  # test thread. Without this, user records created in setup blocks are invisible
  # to the browser-driven Rails server, causing sign-in failures.
  self.use_transactional_tests = false

  # System tests must run serially — the Capybara Puma server is a shared
  # singleton and parallel workers race on the non-transactional test DB.
  # Override the parallelize(workers: :number_of_processors) set in test_helper.rb
  # so that each system test file runs in a single process.
  parallelize(workers: 1)

  driven_by :selenium, using: :headless_chrome, screen_size: [ 1400, 900 ] do |options|
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
  end

  # Helper: sign in a user via the email+password form.
  #
  # Creates the user with a known test password if it doesn't exist, then
  # submits the sign-in form. This is the most reliable approach for Capybara
  # system tests — it goes through the real sessions#create flow.
  #
  # Usage:
  #   sign_in_as(email: "user@example.com")
  #   visit root_url
  #   assert_text "user@example.com"
  TEST_PASSWORD = "test-password-system-tests-fixed"

  def sign_in_as(email:, name: "Test User")
    # Destroy any existing user with this email so we always start from a known
    # state — avoids stale bcrypt hashes from prior test runs causing auth failures.
    # Uses destroy_all (not delete_all) so dependent sessions are removed first
    # via the has_many :sessions, dependent: :destroy callback, preventing FK errors.
    User.where(email_address: email.strip.downcase).destroy_all

    User.create!(
      email_address: email.strip.downcase,
      name:          name,
      provider:      nil,   # email+password user for test purposes
      uid:           nil,
      password:      TEST_PASSWORD
    )

    # Submit the sign-in form. Retry once if the first attempt lands back on
    # the sign-in page — this guards against the rare case where Puma's bcrypt
    # timing causes the form POST to miss its window on a loaded test machine.
    2.times do
      visit new_session_url
      fill_in "email_address", with: email
      fill_in "password",      with: TEST_PASSWORD
      click_on "Sign in"
      # If we're authenticated on root (or anywhere except sign-in), we're done.
      break unless current_url.include?("session") && !page.has_text?("signed in as")
    end

    email
  end

  def sign_in_as_google(email:, name: "Test User", uid: nil)
    sign_in_as(email: email, name: name)
  end

  def sign_out_omniauth
    # Noop — kept for backward compatibility
  end

  # Teardown: destroy all test-created sessions so the browser's session_id
  # cookie from this test is invalidated before the next test runs. The cookie
  # itself stays in the browser (we don't clear it) but pointing to a deleted
  # session, so Puma's find_session_by_cookie returns nil on the next request.
  # sign_in_as then creates a new session whose cookie overwrites the old one.
  teardown do
    Session.where(
      user_id: User.where("email_address LIKE ? OR email_address LIKE ?",
                          "%@example.com", "%@gmail.com").select(:id)
    ).delete_all rescue nil
  end
end
