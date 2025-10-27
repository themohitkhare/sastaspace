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
    assert body["data"]["refresh_token"].present?, "Expected refresh token in response"
    assert body["data"]["user"]["email"] == user_data[:email], "Expected user email in response"
    assert body["data"]["user"]["first_name"] == user_data[:first_name], "Expected first name in response"
    assert_not body["data"]["user"]["password_digest"].present?, "Password digest should not be exposed"

    # Verify user was created
    user = User.find_by(email: user_data[:email])
    assert user.present?, "User should be created"
    assert user.authenticate(user_data[:password]), "User should be able to authenticate with password"
    assert user.refresh_tokens.count > 0, "Refresh token should be created"
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

  test "POST /api/v1/auth/login with valid credentials returns JWT and refresh token" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    post "/api/v1/auth/login", params: {
      email: user.email,
      password: "Password123!"
    }.to_json, headers: api_v1_headers

    assert_success_response
    body = json_response

    assert body["data"]["token"].present?, "Expected JWT token in response"
    assert body["data"]["refresh_token"].present?, "Expected refresh token in response"
    assert body["data"]["user"]["email"] == user.email, "Expected user email in response"
    assert_not body["data"]["user"]["password_digest"].present?, "Password digest should not be exposed"

    # Verify refresh token was created
    assert RefreshToken.where(user: user, token: body["data"]["refresh_token"]).exists?, "Refresh token should exist in database"
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
    refresh_token = RefreshToken.create_for_user!(user)

    post "/api/v1/auth/refresh", params: {
      refresh_token: refresh_token.token
    }.to_json, headers: api_v1_headers

    assert_success_response
    body = json_response

    assert body["data"]["token"].present?, "Expected new JWT token"
    assert body["data"]["refresh_token"].present?, "Expected new refresh token"
    assert body["data"]["refresh_token"] != refresh_token.token, "New refresh token should be different"

    # Old refresh token should be blacklisted
    refresh_token.reload
    assert refresh_token.blacklisted?, "Old refresh token should be blacklisted"

    # New refresh token should be in database
    assert RefreshToken.where(token: body["data"]["refresh_token"]).exists?, "New refresh token should exist"
  end

  test "POST /api/v1/auth/refresh rotates token and prevents reuse" do
    user = create(:user)
    refresh_token = RefreshToken.create_for_user!(user)
    original_token = refresh_token.token

    # First refresh
    post "/api/v1/auth/refresh", params: {
      refresh_token: original_token
    }.to_json, headers: api_v1_headers

    assert_success_response
    body1 = json_response
    new_refresh_token = body1["data"]["refresh_token"]

    # Try to reuse the old token - should fail
    post "/api/v1/auth/refresh", params: {
      refresh_token: original_token
    }.to_json, headers: api_v1_headers

    assert_error_response(:unauthorized, "AUTHENTICATION_ERROR")
    body2 = json_response
    assert_match(/revoked|invalid/i, body2["error"]["message"])

    # New token should still work
    post "/api/v1/auth/refresh", params: {
      refresh_token: new_refresh_token
    }.to_json, headers: api_v1_headers

    assert_success_response
  end

  test "POST /api/v1/auth/refresh with expired token returns error" do
    user = create(:user)
    refresh_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.ago,
      blacklisted: false
    )

    post "/api/v1/auth/refresh", params: {
      refresh_token: refresh_token.token
    }.to_json, headers: api_v1_headers

    assert_error_response(:unauthorized, "AUTHENTICATION_ERROR")
  end

  test "POST /api/v1/auth/refresh with invalid refresh token returns 401" do
    post "/api/v1/auth/refresh", params: {
      refresh_token: "invalid_refresh_token"
    }.to_json, headers: api_v1_headers

    assert_unauthorized_response
  end

  test "POST /api/v1/auth/logout_all revokes all user refresh tokens" do
    user = create(:user)
    access_token = generate_access_token(user)

    # Create multiple refresh tokens for the user
    token1 = RefreshToken.create_for_user!(user)
    token2 = RefreshToken.create_for_user!(user)
    token3 = RefreshToken.create_for_user!(user)

    assert_equal 3, user.refresh_tokens.count, "Should have 3 refresh tokens"
    assert_equal 0, user.refresh_tokens.blacklisted.count, "No tokens should be blacklisted yet"

    post "/api/v1/auth/logout_all", headers: api_v1_headers(access_token)

    assert_success_response

    # All refresh tokens should be blacklisted
    user.refresh_tokens.reload
    assert_equal 3, user.refresh_tokens.blacklisted.count, "All tokens should be blacklisted"

    # Try to use a blacklisted refresh token
    post "/api/v1/auth/refresh", params: {
      refresh_token: token1.token
    }.to_json, headers: api_v1_headers

    assert_error_response(:unauthorized, "AUTHENTICATION_ERROR")

    # Access token should also be blacklisted
    get "/api/v1/auth/me", headers: api_v1_headers(access_token)
    assert_unauthorized_response
  end

  test "POST /api/v1/auth/logout revokes current access token" do
    user = create(:user)
    access_token = generate_access_token(user)

    post "/api/v1/auth/logout", headers: api_v1_headers(access_token)

    assert_success_response

    # Access token should be blacklisted
    get "/api/v1/auth/me", headers: api_v1_headers(access_token)
    assert_unauthorized_response
  end

  test "password change invalidates all refresh tokens" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    # Create some refresh tokens
    token1 = RefreshToken.create_for_user!(user)
    token2 = RefreshToken.create_for_user!(user)

    assert_equal 0, user.refresh_tokens.blacklisted.count, "No tokens should be blacklisted yet"

    # Change password
    user.update!(password: "NewPassword123!", password_confirmation: "NewPassword123!")

    # All refresh tokens should be blacklisted
    user.refresh_tokens.reload
    assert_equal 2, user.refresh_tokens.blacklisted.count, "All tokens should be blacklisted after password change"

    # Try to use a token after password change
    post "/api/v1/auth/refresh", params: {
      refresh_token: token1.token
    }.to_json, headers: api_v1_headers

    assert_error_response(:unauthorized, "AUTHENTICATION_ERROR")
  end

  private

  def generate_access_token(user)
    Auth::JsonWebToken.encode_access_token(user_id: user.id)
  end

  def generate_jwt_token(user)
    Auth::JsonWebToken.encode_access_token(user_id: user.id)
  end
end
