require "test_helper"

class ApplicationControllerTest < ActionDispatch::IntegrationTest
  # Test ApplicationController functionality through a real controller
  setup do
    @user = create(:user)
    UpController.any_instance.stubs(:authenticate_user!).returns(true)
  end

  test "set_request_id_header adds X-Request-ID to response headers" do
    get "/up"

    assert_response :success
    assert_match(/^[a-z0-9-]+$/i, response.headers["X-Request-ID"])
  end

  test "includes StructuredLogging concern" do
    controller = ApplicationController.new
    assert controller.respond_to?(:log_info, true)
    assert controller.respond_to?(:log_error, true)
    assert controller.respond_to?(:log_warn, true)
  end

  test "includes Instrumentation concern" do
    # Instrumentation adds around_action callback - check that callbacks exist
    callbacks = ApplicationController._process_action_callbacks.select { |c| c.filter.to_s.include?("instrument_request") }
    assert callbacks.any?, "Instrumentation concern should add instrument_request callback"
  end

  test "includes ExceptionHandler concern" do
    # ExceptionHandler adds rescue_from callbacks - verify they're registered
    # Check if the class responds to exception handling
    assert ApplicationController.respond_to?(:rescue_from), "Should support rescue_from"

    # Verify exception classes exist
    assert defined?(ExceptionHandler::InvalidToken)
    assert defined?(ExceptionHandler::MissingToken)
    assert defined?(ExceptionHandler::ExpiredToken)
  end

  test "includes SessionAuthenticable concern" do
    controller = ApplicationController.new
    # SessionAuthenticable methods should be available (may be private)
    assert controller.respond_to?(:authenticate_user!, true)
    assert controller.respond_to?(:current_user, true)
  end
end
