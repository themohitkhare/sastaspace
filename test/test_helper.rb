ENV["RAILS_ENV"] ||= "test"

# SimpleCov is only loaded when coverage is explicitly requested
# This allows fast parallel test runs for development/debugging
# Use COVERAGE=1 or SIMPLECOV=1 to enable coverage (e.g., in bin/ci)
enable_coverage = ENV["COVERAGE"] == "1" || ENV["SIMPLECOV"] == "1" || ENV["CI"] == "true"

if enable_coverage
  # SimpleCov must be loaded before any application code
  require "simplecov"

  # Configure SimpleCov for parallel testing
  # Give every process a unique command name to avoid clobbering results
  worker_id = ENV["TEST_ENV_NUMBER"] || ENV["PARALLEL_WORKERS"] || nil
  SimpleCov.command_name(
    [
      "minitest",
      (worker_id && "w#{worker_id}"),
      "pid#{Process.pid}"
    ].compact.join("-")
  )

  SimpleCov.start "rails" do
    # Only merge coverage at the end (when all workers finish)
    merge_timeout 3600

    # Ensure we track files even if not loaded in a given worker
    track_files "app/**/*.rb"

    add_filter "/bin/"
    add_filter "/db/"
    add_filter "/spec/"
    add_filter "/config/"
    add_filter "/vendor/"

    add_group "Models", "app/models"
    add_group "Controllers", "app/controllers"
    add_group "Services", "app/services"
    add_group "Jobs", "app/jobs"
    add_group "Mailers", "app/mailers"
    add_group "Helpers", "app/helpers"

    # Only enforce minimum coverage on CI or when SIMPLECOV/COVERAGE env var is explicitly set
    if ENV["CI"] || ENV["COVERAGE"] || ENV["SIMPLECOV"] == "1"
      minimum_coverage 85
    end
  end

  # Suppress SimpleCov warnings about coverage data exceeding line counts
  # These warnings occur due to trailing newlines (standard Ruby style)
  # and are harmless - they don't affect coverage accuracy
  module Kernel
    alias_method :original_warn, :warn

    def warn(*messages)
      filtered = messages.reject do |msg|
        msg_str = msg.to_s
        msg_str.include?("coverage data provided by Coverage") && msg_str.include?("exceeds number of lines")
      end
      # Only call original_warn if there are messages to warn about
      # (suppress the filtered warnings silently)
      original_warn(*filtered) unless filtered.empty?
    end
  end
end

require_relative "../config/environment"
require "rails/test_help"
require "minitest/reporters"
require "mocha/minitest"

# Configure Mocha for Minitest
Mocha.configure do |config|
  config.strict_keyword_argument_matching = false
end

# Custom reporter that filters PASS results by default for faster debugging
# Set SHOW_ALL_TESTS=1 to see all test results including PASS
class FilteredSpecReporter < Minitest::Reporters::SpecReporter
  def record(result)
    # Show all tests if SHOW_ALL_TESTS is set, or if test failed/errored
    # Also show all tests in CI mode or when coverage is enabled
    show_all = ENV["SHOW_ALL_TESTS"] == "1" ||
               ENV["TEST_FULL"] == "1" ||
               ENV["CI"] == "true" ||
               ENV["COVERAGE"] == "1" ||
               ENV["SIMPLECOV"] == "1"
    should_show = show_all || result.failure || result.error?

    if should_show
      # Show this test result
      super
    else
      # Still record the result for summary statistics, just don't print the line
      # The parent class will handle the summary at the end
      @results << result unless @results.include?(result)
    end
  end
end

# Configure minitest reporters
Minitest::Reporters.use!(
  FilteredSpecReporter.new,
  ENV,
  Minitest.backtrace_filter
)

module ActiveSupport
  class TestCase
    # Enable parallel testing for faster iteration during development
    # Disable when coverage is enabled to avoid coverage merge issues
    # Check environment variables directly to avoid scope issues
    unless ENV["COVERAGE"] == "1" || ENV["SIMPLECOV"] == "1" || ENV["CI"] == "true"
      parallelize(workers: :number_of_processors)
    end

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    # Add more helper methods to be used by all tests here...

    # Clean up after each test
    def teardown
      super
      # No Redis cleanup needed since we're using PostgreSQL
    end
  end
end

# Load support files
Dir[Rails.root.join("test", "support", "**", "*.rb")].each { |f| require f }

# Optionally collate results from multiple workers or separate suites
# Enable by setting SIMPLECOV_COLLATE=1 on the final run
# Only relevant when coverage is enabled
if (ENV["COVERAGE"] == "1" || ENV["SIMPLECOV"] == "1" || ENV["CI"] == "true") && ENV["SIMPLECOV_COLLATE"] == "1"
  at_exit do
    begin
      require "simplecov"
      SimpleCov.collate Dir[File.join("coverage", "**", ".resultset*.json")] do
        formatter SimpleCov::Formatter::HTMLFormatter
      end
    rescue StandardError => e
      warn "SimpleCov collate failed: #{e.message}"
    end
  end
end
