require "test_helper"

class Auth::SessionServiceTest < ActiveSupport::TestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "Password123", password_confirmation: "Password123")
  end

  test "login with remember_me creates refresh token with 30 day expiration" do
    response = Auth::SessionService.login(@user.email, "Password123", nil, remember_me: true)

    assert response[:success], "Login should succeed"
    assert response[:data][:token].present?, "Should return access token"
    assert response[:data][:refresh_token].present?, "Should return refresh token"

    # Find the refresh token in database
    refresh_token = RefreshToken.find_by(token: response[:data][:refresh_token])
    assert refresh_token.present?, "Refresh token should be created in database"

    # Check expiration is approximately 30 days (allow 1 day tolerance)
    expected_expiry = 30.days.from_now
    assert_in_delta expected_expiry.to_i, refresh_token.expires_at.to_i, 1.day.to_i,
      "Refresh token should expire in approximately 30 days"
  end

  test "login without remember_me creates refresh token with 7 day expiration" do
    response = Auth::SessionService.login(@user.email, "Password123", nil, remember_me: false)

    assert response[:success], "Login should succeed"
    assert response[:data][:token].present?, "Should return access token"
    assert response[:data][:refresh_token].present?, "Should return refresh token"

    # Find the refresh token in database
    refresh_token = RefreshToken.find_by(token: response[:data][:refresh_token])
    assert refresh_token.present?, "Refresh token should be created in database"

    # Check expiration is approximately 7 days (allow 1 day tolerance)
    expected_expiry = 7.days.from_now
    assert_in_delta expected_expiry.to_i, refresh_token.expires_at.to_i, 1.day.to_i,
      "Refresh token should expire in approximately 7 days"
  end

  test "login with invalid credentials returns error" do
    response = Auth::SessionService.login(@user.email, "wrongpassword", nil, remember_me: false)

    assert_not response[:success], "Login should fail"
    assert response[:error].present?, "Should return error"
    assert_equal "AUTHENTICATION_ERROR", response[:error][:code]
  end

  test "login with non-existent email returns error" do
    response = Auth::SessionService.login("nonexistent@example.com", "Password123", nil, remember_me: false)

    assert_not response[:success], "Login should fail"
    assert response[:error].present?, "Should return error"
    assert_equal "AUTHENTICATION_ERROR", response[:error][:code]
  end

  test "login handles exceptions gracefully" do
    User.stubs(:find_by).raises(StandardError.new("Database error"))

    response = Auth::SessionService.login(@user.email, "Password123", nil, remember_me: false)

    assert_not response[:success], "Login should fail on exception"
    assert response[:error].present?
    assert_equal "AUTHENTICATION_ERROR", response[:error][:code]
    assert_includes response[:error][:message], "Database error"
  end

  test "register creates new user successfully" do
    user_params = {
      email: "newuser@example.com",
      first_name: "New",
      last_name: "User",
      password: "Password123",
      password_confirmation: "Password123"
    }

    response = Auth::SessionService.register(user_params, nil)

    assert response[:success], "Registration should succeed"
    assert response[:data][:token].present?, "Should return access token"
    assert response[:data][:refresh_token].present?, "Should return refresh token"
    assert_equal "newuser@example.com", response[:data][:user][:email]

    # Verify user was created in database
    user = User.find_by(email: "newuser@example.com")
    assert user.present?, "User should be created"
  end

  test "register with invalid params returns validation errors" do
    user_params = {
      email: "invalid-email",  # Invalid email format
      first_name: "",
      last_name: "",
      password: "short",  # Too short
      password_confirmation: "different"
    }

    response = Auth::SessionService.register(user_params, nil)

    assert_not response[:success], "Registration should fail"
    assert response[:error].present?
    assert_equal "VALIDATION_ERROR", response[:error][:code]
    assert response[:error][:details].present?, "Should include validation details"
  end

  test "register with duplicate email returns validation errors" do
    user_params = {
      email: @user.email,  # Already exists
      first_name: "Test",
      last_name: "User",
      password: "Password123",
      password_confirmation: "Password123"
    }

    response = Auth::SessionService.register(user_params, nil)

    assert_not response[:success], "Registration should fail with duplicate email"
    assert response[:error].present?
    assert_equal "VALIDATION_ERROR", response[:error][:code]
  end

  test "register handles exceptions gracefully" do
    User.stubs(:new).raises(StandardError.new("Database connection failed"))

    user_params = {
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      password: "Password123",
      password_confirmation: "Password123"
    }

    response = Auth::SessionService.register(user_params, nil)

    assert_not response[:success], "Registration should fail on exception"
    assert response[:error].present?
    assert_equal "REGISTRATION_ERROR", response[:error][:code]
    assert_includes response[:error][:message], "Database connection failed"
  end

  test "register accepts hash with string keys" do
    user_params = {
      "email" => "stringkeys@example.com",
      "first_name" => "String",
      "last_name" => "Keys",
      "password" => "Password123",
      "password_confirmation" => "Password123"
    }

    response = Auth::SessionService.register(user_params, nil)

    assert response[:success], "Should handle string keys"
    assert_equal "stringkeys@example.com", response[:data][:user][:email]
  end
end
