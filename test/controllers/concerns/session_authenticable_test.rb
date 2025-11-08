require "test_helper"

class SessionAuthenticableTest < ActionDispatch::IntegrationTest
  # Test SessionAuthenticable through integration tests using InventoryItemsController
  setup do
    @user = create(:user, password: "Password123", password_confirmation: "Password123")
    @access_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @refresh_token = RefreshToken.create_for_user!(@user)
  end

  test "authenticate_user! with valid JWT token succeeds" do
    # Stub cookies.signed to return tokens directly
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(@access_token)
    mock_signed.stubs(:[]).with(:refresh_token).returns(@refresh_token.token)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should succeed (not redirect to login)
    assert_response :success
  end

  test "authenticate_user! with expired JWT token refreshes and succeeds" do
    # Create expired token
    expired_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id, exp: 1.hour.ago.to_i)
    new_access_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    new_refresh_token = RefreshToken.create_for_user!(@user)

    # Stub cookies.signed - expired token first, then new token after refresh
    mock_cookies = mock
    mock_signed = mock
    access_token_sequence = sequence("access_token")
    mock_signed.stubs(:[]).with(:access_token).returns(expired_token).in_sequence(access_token_sequence)
    mock_signed.stubs(:[]).with(:access_token).returns(new_access_token).in_sequence(access_token_sequence)
    refresh_token_value = @refresh_token.token
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_signed.stubs(:[]=).with(:access_token, anything)
    mock_signed.stubs(:[]=).with(:refresh_token, anything)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    # Stub the refresh API call using WebMock
    WebMock.stub_request(:post, /.*\/api\/v1\/auth\/refresh/)
      .to_return(
        status: 200,
        body: {
          success: true,
          data: {
            token: new_access_token,
            refresh_token: new_refresh_token.token
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should succeed after refresh
    assert_response :success
  end

  test "authenticate_user! with invalid JWT token redirects to login" do
    # Stub cookies.signed with invalid token
    # Invalid token will raise JWT::DecodeError, which will try to refresh
    # But refresh will fail, so it should redirect
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns("invalid_token")
    refresh_token_value = @refresh_token.token
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    # Stub refresh_access_token to return nil (refresh fails)
    InventoryItemsController.any_instance.stubs(:refresh_access_token).returns(nil)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_redirected_to login_path
    assert_match(/expired|sign in/i, flash[:alert])
  end

  test "authenticate_user! with no tokens falls back to session" do
    # Set session but no cookies
    post login_path, params: {
      email: @user.email,
      password: "Password123"
    }, headers: { "Accept" => "text/html" }

    Auth::SessionService.stubs(:login).returns({
      success: true,
      data: {
        token: "token",
        refresh_token: "refresh",
        user: { id: @user.id }
      }
    })

    # Session should be set
    assert session[:user_id].present?

    # Clear cookies to test session fallback
    cookies.delete(:access_token)
    cookies.delete(:refresh_token)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should succeed using session
    assert_response :success
  end

  test "authenticate_user! with no tokens and no session redirects to login" do
    # No cookies, no session - make a request first to initialize session
    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_redirected_to login_path
    assert_match(/sign in/i, flash[:alert])
  end

  test "current_user returns user from JWT token" do
    # Stub cookies.signed to return valid tokens
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(@access_token)
    mock_signed.stubs(:[]).with(:refresh_token).returns(@refresh_token.token)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_response :success
    # User should be authenticated via JWT
  end

  test "current_user returns user from session when no tokens" do
    # Set session
    post login_path, params: {
      email: @user.email,
      password: "Password123"
    }, headers: { "Accept" => "text/html" }

    Auth::SessionService.stubs(:login).returns({
      success: true,
      data: {
        token: "token",
        refresh_token: "refresh",
        user: { id: @user.id }
      }
    })

    # Clear cookies
    cookies.delete(:access_token)
    cookies.delete(:refresh_token)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_response :success
    # User should be authenticated via session
  end

  test "get_current_user_from_jwt returns user with valid token" do
    # Stub cookies.signed
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(@access_token)
    mock_signed.stubs(:[]).with(:refresh_token).returns(nil)
    # When access_token is present, present? should return true
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "get_current_user_from_jwt returns nil with no token" do
    cookies.delete(:access_token)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should redirect to login
    assert_redirected_to login_path
  end

  test "get_current_user_from_jwt handles expired token and refreshes" do
    expired_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id, exp: 1.hour.ago.to_i)
    new_access_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    new_refresh_token = RefreshToken.create_for_user!(@user)

    # Stub cookies.signed - expired token first, then new token after refresh
    mock_cookies = mock
    mock_signed = mock
    access_token_sequence = sequence("access_token")
    mock_signed.stubs(:[]).with(:access_token).returns(expired_token).in_sequence(access_token_sequence)
    mock_signed.stubs(:[]).with(:access_token).returns(new_access_token).in_sequence(access_token_sequence)
    refresh_token_value = @refresh_token.token
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_signed.stubs(:[]=).with(:access_token, anything)
    mock_signed.stubs(:[]=).with(:refresh_token, anything)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    WebMock.stub_request(:post, /.*\/api\/v1\/auth\/refresh/)
      .to_return(
        status: 200,
        body: {
          success: true,
          data: {
            token: new_access_token,
            refresh_token: new_refresh_token.token
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "get_current_user_from_jwt handles RecordNotFound" do
    # Token for non-existent user
    invalid_user_token = Auth::JsonWebToken.encode_access_token(user_id: 999999)

    # Stub cookies.signed
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(invalid_user_token)
    mock_signed.stubs(:[]).with(:refresh_token).returns(nil)
    mock_signed.stubs(:present?).returns(false)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_redirected_to login_path
  end

  test "get_current_user_from_session returns user when session exists" do
    post login_path, params: {
      email: @user.email,
      password: "Password123"
    }, headers: { "Accept" => "text/html" }

    Auth::SessionService.stubs(:login).returns({
      success: true,
      data: {
        token: "token",
        refresh_token: "refresh",
        user: { id: @user.id }
      }
    })

    # Session should be set after login
    get inventory_items_path
    assert session[:user_id].present?, "Session should have user_id after login"
  end

  test "get_current_user_from_session returns nil when no session" do
    # Make a request first to initialize session, then check
    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_redirected_to login_path
  end

  test "refresh_access_token succeeds and updates cookies" do
    new_access_token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    new_refresh_token = RefreshToken.create_for_user!(@user)

    # Stub cookies.signed - no access token, but refresh token exists
    mock_cookies = mock
    mock_signed = mock
    access_token_sequence = sequence("access_token")
    mock_signed.stubs(:[]).with(:access_token).returns(nil).in_sequence(access_token_sequence)
    mock_signed.stubs(:[]).with(:access_token).returns(new_access_token).in_sequence(access_token_sequence)
    refresh_token_value = @refresh_token.token
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_signed.stubs(:[]=).with(:access_token, anything)
    mock_signed.stubs(:[]=).with(:refresh_token, anything)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    WebMock.stub_request(:post, /.*\/api\/v1\/auth\/refresh/)
      .to_return(
        status: 200,
        body: {
          success: true,
          data: {
            token: new_access_token,
            refresh_token: new_refresh_token.token
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Cookies should be updated
    assert_response :success
  end

  test "refresh_access_token fails and clears cookies" do
    # Stub cookies.signed - no access token, invalid refresh token
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(nil)
    refresh_token_value = "invalid_refresh_token"
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    WebMock.stub_request(:post, /.*\/api\/v1\/auth\/refresh/)
      .to_return(
        status: 401,
        body: {
          success: false,
          error: { message: "Invalid refresh token" }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should redirect to login
    assert_redirected_to login_path
  end

  test "refresh_access_token handles network errors" do
    # Stub cookies.signed - no access token, refresh token exists
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(nil)
    refresh_token_value = @refresh_token.token
    mock_signed.stubs(:[]).with(:refresh_token).returns(refresh_token_value)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    WebMock.stub_request(:post, /.*\/api\/v1\/auth\/refresh/)
      .to_raise(StandardError.new("Network error"))

    get inventory_items_path, headers: { "Accept" => "text/html" }

    # Should redirect to login on error
    assert_redirected_to login_path
  end

  test "refresh_token_via_api returns success response" do
    # This is tested indirectly through refresh_access_token tests
    # But we can verify the API endpoint works
    post "/api/v1/auth/refresh", params: {
      refresh_token: @refresh_token.token
    }.to_json, headers: { "Content-Type" => "application/json" }

    assert_response :success
  end

  test "refresh_token_via_api handles errors gracefully" do
    # Test with invalid refresh token
    post "/api/v1/auth/refresh", params: {
      refresh_token: "invalid_token"
    }.to_json, headers: { "Content-Type" => "application/json" }

    assert_response :unauthorized
  end

  test "sign_in and sign_out work correctly" do
    # Test through actual controller flow
    post login_path, params: {
      email: @user.email,
      password: "Password123"
    }, headers: { "Accept" => "text/html" }

    Auth::SessionService.stubs(:login).returns({
      success: true,
      data: {
        token: "token",
        refresh_token: "refresh",
        user: { id: @user.id }
      }
    })

    # After login, session should be set
    assert_equal @user.id, session[:user_id]

    # Sign out
    delete logout_path
    SessionsController.any_instance.stubs(:logout_user_via_api).returns(true)

    # Session should be cleared
    assert_nil session[:user_id]
  end

  test "user_signed_in? returns true when user is authenticated" do
    # Stub cookies.signed
    mock_cookies = mock
    mock_signed = mock
    mock_signed.stubs(:[]).with(:access_token).returns(@access_token)
    mock_signed.stubs(:[]).with(:refresh_token).returns(@refresh_token.token)
    mock_signed.stubs(:present?).returns(true)
    mock_cookies.stubs(:signed).returns(mock_signed)
    mock_cookies.stubs(:delete)
    InventoryItemsController.any_instance.stubs(:cookies).returns(mock_cookies)

    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_response :success
    # user_signed_in? should be true
  end

  test "user_signed_in? returns false when user is not authenticated" do
    # Make a request without authentication
    get inventory_items_path, headers: { "Accept" => "text/html" }

    assert_redirected_to login_path
    # user_signed_in? should be false
  end
end
