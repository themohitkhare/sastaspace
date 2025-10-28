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

  def generate_jwt_token(user)
    Auth::JsonWebToken.encode_access_token(user_id: user.id)
  end

  def generate_access_token(user)
    Auth::JsonWebToken.encode_access_token(user_id: user.id)
  end

  def generate_expired_jwt_token(user)
    # Create a token with expired time
    payload = { user_id: user.id, exp: 1.hour.ago.to_i }
    JWT.encode(payload, Rails.application.secret_key_base)
  end
end

# Include in integration tests
class ActionDispatch::IntegrationTest
  include ApiHelpers
end
