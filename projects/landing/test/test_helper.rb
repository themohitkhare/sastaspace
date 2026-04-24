ENV["RAILS_ENV"] ||= "test"

require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    # Run unit tests in parallel; system tests run serially (see ApplicationSystemTestCase).
    parallelize(workers: :number_of_processors)

    # Fixtures are disabled for now: the shared Postgres instance has seed data
    # that overlaps with fixture table names. Individual tests create their own
    # data as needed.
    # fixtures :all

    # Add more helper methods to be used by all tests here...
  end
end
