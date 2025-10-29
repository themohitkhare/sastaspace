require "test_helper"
require "capybara/cuprite"

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  driven_by :cuprite, screen_size: [1400, 1400], options: {
    js_errors: true,
    headless: true,
    inspector: ENV["INSPECTOR"],
    browser_options: {
      "no-sandbox" => nil
    }
  }
end
