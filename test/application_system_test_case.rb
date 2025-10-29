require "test_helper"
require "capybara/cuprite"

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  # Enable parallel testing for system tests
  # Can be disabled with PARALLEL_WORKERS=1 bin/rails test:system
  # Or limit workers: PARALLEL_WORKERS=2 bin/rails test:system
  if ENV["PARALLEL_WORKERS"].present?
    parallelize(workers: ENV["PARALLEL_WORKERS"].to_i)
  else
    parallelize(workers: :number_of_processors)
  end

  driven_by :cuprite, screen_size: [ 1400, 1400 ], options: {
    js_errors: true,
    headless: true,
    inspector: ENV["INSPECTOR"],
    browser_options: {
      "no-sandbox" => nil
    }
  }
end
