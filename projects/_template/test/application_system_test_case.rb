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
end
