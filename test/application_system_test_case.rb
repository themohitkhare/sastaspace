require "test_helper"
require "capybara/cuprite"

class ApplicationSystemTestCase < ActionDispatch::SystemTestCase
  # Ensure DB changes are visible to the app server (no transactional tests)
  self.use_transactional_tests = false

  # Enable parallel system tests
  # Each worker gets its own database and Capybara server port
  # Control worker count via PARALLEL_WORKERS env var (integer), or use :number_of_processors
  worker_count = if ENV["PARALLEL_WORKERS"]
                   ENV["PARALLEL_WORKERS"].to_i
  else
                   :number_of_processors
  end
  parallelize(workers: worker_count, with: :processes)

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

  # Increase waits/timeouts to reduce Ferrum timeouts on slower CI or parallel runs
  Capybara.default_max_wait_time = 5

  driven_by :cuprite, screen_size: [ 1400, 1400 ], options: {
    js_errors: true,
    headless: true,
    inspector: ENV["INSPECTOR"],
    timeout: 15, # seconds to wait for browser operations
    process_timeout: 30, # seconds to wait for the process
    browser_options: {
      "no-sandbox" => nil
    }
  }
end
