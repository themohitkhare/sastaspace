require "test_helper"

class ExceptionHandlerTest < ActionDispatch::IntegrationTest
  # Test ExceptionHandler concern through API controller
  setup do
    @user = create(:user)
  end

  test "invalid_token renders proper JSON response" do
    Api::V1::InventoryItemsController.any_instance.stubs(:authenticate_user!).raises(ExceptionHandler::InvalidToken.new("Invalid token"))

    get "/api/v1/inventory_items", headers: api_v1_headers

    assert_response :unauthorized
    body = json_response
    assert_equal false, body["success"]
    assert_equal "AUTHENTICATION_ERROR", body["error"]["code"]
    assert_equal "Invalid token", body["error"]["message"]
    assert body["timestamp"].present?
  end

  test "missing_token renders proper JSON response" do
    Api::V1::InventoryItemsController.any_instance.stubs(:authenticate_user!).raises(ExceptionHandler::MissingToken.new("Token is missing"))

    get "/api/v1/inventory_items", headers: api_v1_headers

    assert_response :unauthorized
    body = json_response
    assert_equal false, body["success"]
    assert_equal "AUTHENTICATION_ERROR", body["error"]["code"]
    assert_equal "Missing token", body["error"]["message"]
  end

  test "expired_token renders proper JSON response" do
    Api::V1::InventoryItemsController.any_instance.stubs(:authenticate_user!).raises(ExceptionHandler::ExpiredToken.new("Token expired"))

    get "/api/v1/inventory_items", headers: api_v1_headers

    assert_response :unauthorized
    body = json_response
    assert_equal false, body["success"]
    assert_equal "AUTHENTICATION_ERROR", body["error"]["code"]
    assert_equal "Invalid token", body["error"]["message"]
    assert body["error"]["details"].present?
  end
end

