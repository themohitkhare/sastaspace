require "test_helper"
require "capybara/cuprite"

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  # Ensure DB changes are visible to the app server (no transactional tests)
  self.use_transactional_tests = false
  # Run system tests serially to avoid DB visibility issues and flakiness
  parallelize(workers: 1)

  setup do
    tables = %w[
      ai_analyses
      inventory_tags
      tags
      inventory_items
      refresh_tokens
      brands
      categories
      users
    ]
    ActiveRecord::Base.connection.execute(
      "TRUNCATE TABLE #{tables.join(', ')} RESTART IDENTITY CASCADE"
    )
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
