require "test_helper"

class StructuredLoggingTest < ActionDispatch::IntegrationTest
  # Test StructuredLogging concern through integration tests
  setup do
    @user = create(:user)
    UpController.any_instance.stubs(:authenticate_user!).returns(true)
    UpController.any_instance.stubs(:current_user).returns(@user)
  end

  test "sanitize_params removes sensitive fields" do
    # Test sanitize_params through a controller that uses it
    params = {
      email: "test@example.com",
      password: "secret123",
      password_confirmation: "secret123",
      token: "abc123",
      secret: "hidden",
      normal_field: "visible"
    }

    # Access the method through a controller instance
    controller = UpController.new
    sanitized = controller.send(:sanitize_params, params)

    assert_equal "test@example.com", sanitized[:email]
    assert_equal "visible", sanitized[:normal_field]
    assert_nil sanitized[:password]
    assert_nil sanitized[:password_confirmation]
    assert_nil sanitized[:token]
    assert_nil sanitized[:secret]
  end

  test "StructuredLogging concern is included in ApplicationController" do
    # Verify the concern methods are available
    controller = ApplicationController.new
    assert controller.respond_to?(:log_info, true)
    assert controller.respond_to?(:log_error, true)
    assert controller.respond_to?(:log_warn, true)
    assert controller.respond_to?(:sanitize_params, true)
    assert controller.respond_to?(:current_request_id, true)
  end
end
