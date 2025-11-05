ENV["RAILS_ENV"] ||= "test"

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

  # Only enforce minimum coverage on CI or when COVERAGE env var is explicitly set
  if ENV["CI"] || ENV["COVERAGE"]
    minimum_coverage 80
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

# Configure minitest reporters
# By default, only show failures and summary. Use VERBOSE=true for full output.
if ENV["VERBOSE"] == "true" || ENV["V"] == "1"
  # Verbose mode: show all tests with SpecReporter
  Minitest::Reporters.use!(
    Minitest::Reporters::SpecReporter.new,
    ENV,
    Minitest.backtrace_filter
  )
else
  # Default mode: only show failures and summary (quiet mode)
  # Use a minimal reporter that only shows failures and final summary
  class QuietReporter < Minitest::Reporters::BaseReporter
    def initialize(options = {})
      super
      @failures = []
      @errors = []
      @skips = []
      @counts = { total: 0, assertions: 0, failures: 0, errors: 0, skips: 0 }
    end

    def start
      super # Track start_time in parent
      # Suppress "Started with run options" message by not printing anything
    end

    def record(result)
      @counts[:total] += 1
      @counts[:assertions] += result.assertions

      if result.failure
        if result.failure.is_a?(Minitest::UnexpectedError)
          @counts[:errors] += 1
          @errors << result
        else
          @counts[:failures] += 1
          @failures << result
        end
        # Print failure details immediately
        print_failure(result)
      elsif result.skipped?
        @counts[:skips] += 1
        @skips << result
        # Print skip details
        print_skip(result)
      end
      # Don't print anything for passing tests
    end

    def report
      super # Let parent handle timing
      # Print summary at the end
      print_summary
    end

    private

    def print_failure(result)
      puts "\n#{result.class}##{result.name}"
      puts result.failure.message
      puts result.failure.backtrace.first(5).join("\n")
      puts
    end

    def print_skip(result)
      puts "\n#{result.class}##{result.name} SKIPPED"
      puts result.failure.message if result.failure
      puts
    end

    def print_summary
      time = total_time rescue "N/A"
      puts "\n" + "=" * 70
      puts "Finished in #{time}s"
      puts "#{@counts[:total]} tests, #{@counts[:assertions]} assertions, " \
           "#{@counts[:failures]} failures, #{@counts[:errors]} errors, #{@counts[:skips]} skips"
    end
  end

  Minitest::Reporters.use!(
    QuietReporter.new,
    ENV,
    Minitest.backtrace_filter
  )
end

module ActiveSupport
  class TestCase
    # DISABLE parallel testing to ensure SimpleCov works properly
    # Run tests sequentially to get accurate coverage
    # parallelize(workers: :number_of_processors)

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
if ENV["SIMPLECOV_COLLATE"] == "1"
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
