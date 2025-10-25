require "test_helper"

class ApiV1AuthTest < ActionDispatch::IntegrationTest
  def setup
    # Clear token blacklist between tests
    Authenticable.instance_variable_set(:@test_blacklisted_tokens, [])
  end
  test "POST /api/v1/auth/register with valid data creates user and returns JWT" do
    user_data = {
      email: "test@example.com",
      password: "Password123!",
      password_confirmation: "Password123!",
      first_name: "John",
      last_name: "Doe"
    }

    post "/api/v1/auth/register", params: user_data.to_json, headers: api_v1_headers

    assert_success_response
    body = json_response

    assert body["data"]["token"].present?, "Expected JWT token in response"
    assert body["data"]["user"]["email"] == user_data[:email], "Expected user email in response"
    assert body["data"]["user"]["first_name"] == user_data[:first_name], "Expected first name in response"
    assert_not body["data"]["user"]["password_digest"].present?, "Password digest should not be exposed"

    # Verify user was created
    user = User.find_by(email: user_data[:email])
    assert user.present?, "User should be created"
    assert user.authenticate(user_data[:password]), "User should be able to authenticate with password"
  end

  test "POST /api/v1/auth/register with invalid data returns validation errors" do
    invalid_data = {
      email: "invalid-email",
      password: "weak",
      password_confirmation: "different"
    }

    post "/api/v1/auth/register", params: invalid_data.to_json, headers: api_v1_headers

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response

    assert body["error"]["details"].present?, "Expected validation error details"
    assert body["error"]["details"]["email"].present?, "Expected email validation error"
    assert body["error"]["details"]["password"].present?, "Expected password validation error"
  end

  test "POST /api/v1/auth/register with existing email returns error" do
    existing_user = create(:user, email: "existing@example.com")

    user_data = {
      email: "existing@example.com",
      password: "Password123!",
      password_confirmation: "Password123!"
    }

    post "/api/v1/auth/register", params: user_data.to_json, headers: api_v1_headers

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["details"]["email"].present?, "Expected email uniqueness error"
  end

  test "POST /api/v1/auth/login with valid credentials returns JWT" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    post "/api/v1/auth/login", params: {
      email: user.email,
      password: "Password123!"
    }.to_json, headers: api_v1_headers

    assert_success_response
    body = json_response

    assert body["data"]["token"].present?, "Expected JWT token in response"
    assert body["data"]["user"]["email"] == user.email, "Expected user email in response"
    assert_not body["data"]["user"]["password_digest"].present?, "Password digest should not be exposed"
  end

  test "POST /api/v1/auth/login with invalid credentials returns 401" do
    post "/api/v1/auth/login", params: {
      email: "nope@example.com",
      password: "wrong"
    }.to_json, headers: api_v1_headers

    assert_unauthorized_response
  end

  test "POST /api/v1/auth/login with wrong password returns 401" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    post "/api/v1/auth/login", params: {
      email: user.email,
      password: "WrongPassword123!"
    }.to_json, headers: api_v1_headers

    assert_unauthorized_response
  end

  test "GET /api/v1/auth/me with valid token returns user data" do
    user = create(:user)
    token = generate_jwt_token(user)

    get "/api/v1/auth/me", headers: api_v1_headers(token)

    assert_success_response
    body = json_response

    assert body["data"]["user"]["email"] == user.email, "Expected user email in response"
    assert body["data"]["user"]["id"] == user.id, "Expected user ID in response"
  end

  test "GET /api/v1/auth/me without token returns 401" do
    get "/api/v1/auth/me", headers: api_v1_headers

    assert_unauthorized_response
  end

  test "GET /api/v1/auth/me with invalid token returns 401" do
    get "/api/v1/auth/me", headers: api_v1_headers("invalid_token")

    assert_unauthorized_response
  end

  test "POST /api/v1/auth/refresh with valid refresh token returns new tokens" do
    user = create(:user)
    refresh_token = generate_refresh_token(user)

    post "/api/v1/auth/refresh", params: {
      refresh_token: refresh_token
    }.to_json, headers: api_v1_headers

    assert_success_response
    body = json_response

    assert body["data"]["token"].present?, "Expected new JWT token"
    assert body["data"]["refresh_token"].present?, "Expected new refresh token"
    assert body["data"]["token"] != refresh_token, "New token should be different"
  end

  test "POST /api/v1/auth/refresh with invalid refresh token returns 401" do
    post "/api/v1/auth/refresh", params: {
      refresh_token: "invalid_refresh_token"
    }.to_json, headers: api_v1_headers

    assert_unauthorized_response
  end

  test "POST /api/v1/auth/logout_all revokes all user tokens" do
    user = create(:user)
    token = generate_jwt_token(user)

    post "/api/v1/auth/logout_all", headers: api_v1_headers(token)

    assert_success_response

    # Verify token is now invalid
    get "/api/v1/auth/me", headers: api_v1_headers(token)
    assert_unauthorized_response
  end

  private

  def generate_jwt_token(user)
    Auth::JsonWebToken.encode(user_id: user.id)
  end

  def generate_refresh_token(user)
    # For now, return a placeholder since refresh tokens aren't implemented
    "refresh_token_for_#{user.id}"
  end
end
