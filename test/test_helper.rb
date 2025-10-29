ENV["RAILS_ENV"] ||= "test"

# SimpleCov must be loaded before any application code
require "simplecov"

# Configure SimpleCov for parallel testing
# In parallel mode, each worker gets a unique process ID
if ENV["PARALLEL_WORKERS"]
  SimpleCov.command_name "test_#{ENV['TEST_ENV_NUMBER'] || 0}"
end

SimpleCov.start "rails" do
  # Only merge coverage at the end (when all workers finish)
  merge_timeout 3600

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
Minitest::Reporters.use!(
  Minitest::Reporters::SpecReporter.new,
  ENV,
  Minitest.backtrace_filter
)

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
