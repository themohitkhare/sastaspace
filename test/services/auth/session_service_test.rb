require "test_helper"

class Auth::SessionServiceTest < ActiveSupport::TestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "password123")
  end

  test "login with remember_me creates refresh token with 30 day expiration" do
    response = Auth::SessionService.login(@user.email, "password123", nil, remember_me: true)

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
    response = Auth::SessionService.login(@user.email, "password123", nil, remember_me: false)

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
    response = Auth::SessionService.login("nonexistent@example.com", "password123", nil, remember_me: false)

    assert_not response[:success], "Login should fail"
    assert response[:error].present?, "Should return error"
    assert_equal "AUTHENTICATION_ERROR", response[:error][:code]
  end
end

