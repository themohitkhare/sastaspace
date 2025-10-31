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
    controller = ApplicationController.new
    # Instrumentation adds around_action callback
    assert ApplicationController._process_action_callbacks.any? { |c| c.filter.to_s.include?("instrument_request") }
  end

  test "includes ExceptionHandler concern" do
    # ExceptionHandler adds rescue_from callbacks
    assert ApplicationController.rescue_handlers.any? { |handler| handler.first == ExceptionHandler::InvalidToken }
    assert ApplicationController.rescue_handlers.any? { |handler| handler.first == ExceptionHandler::MissingToken }
    assert ApplicationController.rescue_handlers.any? { |handler| handler.first == ExceptionHandler::ExpiredToken }
  end

  test "includes SessionAuthenticable concern" do
    controller = ApplicationController.new
    assert controller.respond_to?(:authenticate_user!)
    assert controller.respond_to?(:current_user)
  end
end

