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
      outfit_items
      outfits
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

  # Helper method to navigate to outfits page reliably
  def visit_outfits
    # If already showing outfits content, return early
    return if page.has_selector?("h1", text: /My Outfits/i, wait: 0)

    # Strategy 1: Click navigation link (preserves session/cookies)
    if page.has_link?("Outfits", wait: 5)
      # Try clicking the link
      begin
        click_link "Outfits"
      rescue => e
        # Fallback to JavaScript click if regular click fails
        outfits_link = find_link("Outfits", wait: 2)
        page.execute_script("arguments[0].click();", outfits_link) if outfits_link
      end

      # Wait for content to appear (more reliable than checking path)
      # Give it time for Turbo/JavaScript to load
      sleep 2

      # Check if outfits content is visible
      if page.has_selector?("h1", text: /My Outfits/i, wait: 5)
        return
      end
    end

    # Strategy 2: Direct visit (should work if session is maintained)
    visit "/outfits"
    sleep 2

    # Wait for content instead of checking path
    # The page might be loading correctly but path check might be wrong
    unless page.has_selector?("h1", text: /My Outfits/i, wait: 5)
      # If still not showing outfits content, we might have an issue
      # But don't raise - let the test handle it with proper assertions
    end
  end

  # Helper to ensure we're on outfits page
  def ensure_on_outfits_page
    # Try multiple times if needed
    3.times do
      return if page.has_selector?("h1", text: /My Outfits/i, wait: 0)
      visit_outfits
      sleep 1
    end

    # Final check with assertion - check content, not path
    assert_selector("h1", text: /My Outfits/i, wait: 5)
  end
end
