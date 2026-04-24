ENV["RAILS_ENV"] ||= "test"

require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers
    parallelize(workers: :number_of_processors)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    # Helper: stub a session for the given user so integration tests don't
    # need to go through OmniAuth round-trips.
    def sign_in_as(user)
      session_record = user.sessions.create!(user_agent: "test", ip_address: "127.0.0.1")
      cookies.signed[:session_id] = session_record.id
    end
  end
end
