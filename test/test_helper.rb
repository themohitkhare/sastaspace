ENV["RAILS_ENV"] ||= "test"

# SimpleCov must be loaded before any application code
require "simplecov"
SimpleCov.start "rails" do
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

  minimum_coverage 85
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
    # Run tests in parallel with specified workers
    parallelize(workers: :number_of_processors)

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
