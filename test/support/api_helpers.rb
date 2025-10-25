# API test helpers for consistent request/response testing
module ApiHelpers
  def json_response
    JSON.parse(@response.body)
  end

  def assert_success_response
    assert_response :success
    body = json_response
    assert body["success"], "Expected success envelope"
    assert body["data"].present?, "Expected data in response"
    assert body["timestamp"].present?, "Expected timestamp in response"
  end

  def assert_error_response(status = :unprocessable_entity, error_code = nil)
    assert_response status
    body = json_response
    assert body["success"] == false, "Expected error envelope"
    assert body["error"].present?, "Expected error details"
    assert body["error"]["code"].present?, "Expected error code"
    assert_equal error_code, body["error"]["code"] if error_code
  end

  def assert_unauthorized_response
    assert_error_response(:unauthorized, "AUTHENTICATION_ERROR")
  end

  def assert_forbidden_response
    assert_error_response(:forbidden, "AUTHORIZATION_ERROR")
  end

  def assert_not_found_response
    assert_error_response(:not_found, "NOT_FOUND")
  end

  def auth_headers(token)
    { "Authorization" => "Bearer #{token}" }
  end

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!(auth_headers(token)) if token
    headers
  end
end

# Include in integration tests
class ActionDispatch::IntegrationTest
  include ApiHelpers
end
