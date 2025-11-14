require "test_helper"

class AuditLoggingTest < ActionDispatch::IntegrationTest
  # Test AuditLogging through a test controller
  class TestAuditController < Api::V1::BaseController
    include AuditLogging

    def index
      log_security_event("test_event", { test: "data" })
      render json: { message: "success" }, status: :ok
    end

    def auth_action
      log_auth_event("login", { method: "password" })
      render json: { message: "success" }, status: :ok
    end

    def data_access_action
      log_data_access_event("InventoryItem", 123, "read", { field: "name" })
      render json: { message: "success" }, status: :ok
    end

    def data_modification_action
      log_data_modification_event("InventoryItem", 123, "update", { field: "name", old_value: "old", new_value: "new" })
      render json: { message: "success" }, status: :ok
    end
  end

  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    # Create fresh StringIO for each test to prevent state leakage
    @logger_output = StringIO.new
    # Stub logger to capture output (replaces any previous stub)
    Rails.logger.stubs(:info).with { |arg| @logger_output.write(arg.to_s + "\n"); true }

    Rails.application.routes.draw do
      get "/test_audit", to: "audit_logging_test/test_audit#index"
      get "/test_audit/auth", to: "audit_logging_test/test_audit#auth_action"
      get "/test_audit/data_access", to: "audit_logging_test/test_audit#data_access_action"
      get "/test_audit/data_modification", to: "audit_logging_test/test_audit#data_modification_action"
    end
  end

  teardown do
    # Clean up logger stub to prevent interference with other tests
    Rails.logger.unstub_all if Rails.logger.respond_to?(:unstub_all)
    # Close and clear logger output to prevent state leakage
    @logger_output&.close
    @logger_output = nil
    # Reload routes to clean up test routes
    Rails.application.routes_reloader.reload!
  end

  test "log_security_event logs security event with user context" do
    get "/test_audit", headers: api_v1_headers(@token)

    output = @logger_output.string
    assert_match(/\[AUDIT\]/, output)
    assert_match(/test_event/, output)
    assert_match(/test/, output)
    assert_match(/data/, output)
  end

  test "log_auth_event logs authentication event" do
    get "/test_audit/auth", headers: api_v1_headers(@token)

    output = @logger_output.string
    assert_match(/\[AUDIT\]/, output)
    assert_match(/auth:login/, output)
    assert_match(/method/, output)
    assert_match(/password/, output)
  end

  test "log_data_access_event logs data access event" do
    get "/test_audit/data_access", headers: api_v1_headers(@token)

    output = @logger_output.string
    assert_match(/\[AUDIT\]/, output)
    assert_match(/data_access/, output)
    assert_match(/InventoryItem/, output)
    assert_match(/123/, output)
    assert_match(/read/, output)
  end

  test "log_data_modification_event logs data modification event" do
    get "/test_audit/data_modification", headers: api_v1_headers(@token)

    output = @logger_output.string
    assert_match(/\[AUDIT\]/, output)
    assert_match(/data_modification/, output)
    assert_match(/InventoryItem/, output)
    assert_match(/123/, output)
    assert_match(/update/, output)
  end

  test "log_security_event includes request context" do
    get "/test_audit", headers: api_v1_headers(@token)

    output = @logger_output.string
    # Should include user_id, ip_address, user_agent, request_id
    assert_match(/user_id/, output)
    assert_match(/ip_address/, output)
    assert_match(/user_agent/, output)
    assert_match(/request_id/, output)
  end

  private

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!("Authorization" => "Bearer #{token}") if token
    headers
  end
end
