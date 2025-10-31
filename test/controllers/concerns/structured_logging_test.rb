require "test_helper"

class StructuredLoggingTest < ActionDispatch::IntegrationTest
  # Test StructuredLogging concern through a real controller
  setup do
    @user = create(:user)
    @controller_instance = UpController.new
    @controller_instance.stubs(:request).returns(mock_request)
    @controller_instance.stubs(:action_name).returns("show")
    @controller_instance.stubs(:current_user).returns(@user)
  end

  test "log_info creates properly formatted log entry" do
    log_io = StringIO.new
    original_logger = Rails.logger
    Rails.logger = Logger.new(log_io)

    @controller_instance.send(:log_info, "Test message", { extra: "data" })

    log_output = log_io.string
    Rails.logger = original_logger

    # Extract JSON from log output (might have timestamp prefix)
    json_line = log_output.lines.find { |line| line.include?('"level":"INFO"') } || log_output
    json_line = json_line.split(" ", 2).last if json_line.include?(" ")
    log_data = JSON.parse(json_line.chomp)
    
    assert_equal "INFO", log_data["level"]
    assert_equal "Test message", log_data["message"]
    assert_equal "data", log_data["extra"]
    assert_equal @user.id, log_data["user_id"]
    assert_equal "UpController", log_data["controller"]
    assert_equal "show", log_data["action"]
    assert log_data["timestamp"].present?
  end

  test "log_error creates properly formatted log entry" do
    log_io = StringIO.new
    original_logger = Rails.logger
    Rails.logger = Logger.new(log_io)

    @controller_instance.send(:log_error, "Error message", { error_code: "E001" })

    log_output = log_io.string
    Rails.logger = original_logger

    json_line = log_output.lines.find { |line| line.include?('"level":"ERROR"') } || log_output
    json_line = json_line.split(" ", 2).last if json_line.include?(" ")
    log_data = JSON.parse(json_line.chomp)

    assert_equal "ERROR", log_data["level"]
    assert_equal "Error message", log_data["message"]
    assert_equal "E001", log_data["error_code"]
  end

  test "log_warn creates properly formatted log entry" do
    log_io = StringIO.new
    original_logger = Rails.logger
    Rails.logger = Logger.new(log_io)

    @controller_instance.send(:log_warn, "Warning message")

    log_output = log_io.string
    Rails.logger = original_logger

    json_line = log_output.lines.find { |line| line.include?('"level":"WARN"') } || log_output
    json_line = json_line.split(" ", 2).last if json_line.include?(" ")
    log_data = JSON.parse(json_line.chomp)

    assert_equal "WARN", log_data["level"]
    assert_equal "Warning message", log_data["message"]
  end

  test "current_request_id returns request ID from env" do
    request = mock_request
    request.env["REQUEST_ID"] = "test-request-123"
    @controller_instance.stubs(:request).returns(request)

    request_id = @controller_instance.send(:current_request_id)
    assert_equal "test-request-123", request_id
  end

  test "current_request_id returns nil when request is not available" do
    @controller_instance.stubs(:request).returns(nil)
    
    request_id = @controller_instance.send(:current_request_id)
    assert_nil request_id
  end

  test "sanitize_params removes sensitive fields" do
    params = {
      email: "test@example.com",
      password: "secret123",
      password_confirmation: "secret123",
      token: "abc123",
      secret: "hidden",
      normal_field: "visible"
    }

    sanitized = @controller_instance.send(:sanitize_params, params)
    
    assert_equal "test@example.com", sanitized[:email]
    assert_equal "visible", sanitized[:normal_field]
    assert_nil sanitized[:password]
    assert_nil sanitized[:password_confirmation]
    assert_nil sanitized[:token]
    assert_nil sanitized[:secret]
  end

  private

  def mock_request
    request = ActionDispatch::TestRequest.create
    request.env["REQUEST_ID"] = "test-request-id"
    request
  end
end

