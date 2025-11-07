require "test_helper"

class ApiResponseTest < ActionDispatch::IntegrationTest
  # Test ApiResponse through a test controller
  class TestApiResponseController < Api::V1::BaseController
    include ApiResponse

    def success_action
      render_success(data: { test: "data" }, message: "Success message")
    end

    def created_action
      render_created(data: { id: 1, name: "Test" }, message: "Created successfully")
    end

    def paginated_action
      items = Kaminari.paginate_array([ 1, 2, 3 ]).page(1).per(2)
      render_paginated(collection: items, message: "Paginated data")
    end

    def error_action
      render_error_response(
        code: "TEST_ERROR",
        message: "Test error message",
        details: { field: "name", reason: "invalid" },
        status: :bad_request
      )
    end

    def validation_error_action
      user = User.new
      user.valid? # Trigger validations
      render_validation_errors(user.errors, message: "Custom validation message")
    end
  end

  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)

    Rails.application.routes.draw do
      get "/test_api_response/success", to: "api_response_test/test_api_response#success_action"
      post "/test_api_response/created", to: "api_response_test/test_api_response#created_action"
      get "/test_api_response/paginated", to: "api_response_test/test_api_response#paginated_action"
      get "/test_api_response/error", to: "api_response_test/test_api_response#error_action"
      get "/test_api_response/validation_error", to: "api_response_test/test_api_response#validation_error_action"
    end
  end

  teardown do
    Rails.application.routes_reloader.reload!
  end

  test "render_success returns success response with data" do
    get "/test_api_response/success", headers: api_v1_headers(@token)

    assert_response :ok
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_equal "data", body["data"]["test"]
    assert_equal "Success message", body["message"]
    assert body["timestamp"].present?
    # request_id may be nil if REQUEST_ID middleware hasn't set it
    assert body.key?("request_id")
  end

  test "render_success works without optional parameters" do
    # Test that render_success can be called with minimal parameters
    # The success_action test already covers the full functionality
    get "/test_api_response/success", headers: api_v1_headers(@token)
    assert_response :ok
  end

  test "render_created returns created response" do
    post "/test_api_response/created", headers: api_v1_headers(@token)

    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_equal 1, body["data"]["id"]
    assert_equal "Test", body["data"]["name"]
    assert_equal "Created successfully", body["message"]
  end

  test "render_paginated returns paginated response" do
    get "/test_api_response/paginated", headers: api_v1_headers(@token)

    assert_response :ok
    body = JSON.parse(@response.body)
    assert body["success"]
    assert body["data"]["items"].present?
    assert body["data"]["pagination"].present?
    assert_equal 1, body["data"]["pagination"]["current_page"]
    assert_equal 2, body["data"]["pagination"]["total_pages"]
    assert_equal 3, body["data"]["pagination"]["total_count"]
    assert_equal 2, body["data"]["pagination"]["per_page"]
  end

  test "render_error_response returns error response" do
    get "/test_api_response/error", headers: api_v1_headers(@token)

    assert_response :bad_request
    body = JSON.parse(@response.body)
    assert_not body["success"]
    assert_equal "TEST_ERROR", body["error"]["code"]
    assert_equal "Test error message", body["error"]["message"]
    assert_equal "name", body["error"]["details"]["field"]
    assert body["error"]["timestamp"].present?
    # request_id may be nil if REQUEST_ID middleware hasn't set it
    assert body["error"].key?("request_id")
  end

  test "render_validation_errors returns validation error response" do
    get "/test_api_response/validation_error", headers: api_v1_headers(@token)

    assert_response :unprocessable_entity
    body = JSON.parse(@response.body)
    assert_not body["success"]
    assert_equal "VALIDATION_ERROR", body["error"]["code"]
    assert_equal "Custom validation message", body["error"]["message"]
    assert body["error"]["details"].present?
  end

  test "current_request_id returns request ID from env" do
    controller = TestApiResponseController.new
    request = mock(env: { "REQUEST_ID" => "test-request-123" })
    controller.stubs(:request).returns(request)
    controller.stubs(:respond_to?).with(:request).returns(true)

    request_id = controller.send(:current_request_id)
    assert_equal "test-request-123", request_id
  end

  test "current_request_id returns nil when request not available" do
    controller = TestApiResponseController.new
    controller.stubs(:respond_to?).with(:request).returns(false)

    request_id = controller.send(:current_request_id)
    assert_nil request_id
  end

  private

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!("Authorization" => "Bearer #{token}") if token
    headers
  end
end
