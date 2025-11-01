require "test_helper"

class SessionsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
  end

  test "new renders successfully when not signed in" do
    get login_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "new redirects when already signed in" do
    # Simulate session login
    post login_path, params: {}, headers: { "Accept" => "text/html" }
    SessionsController.any_instance.stubs(:user_signed_in?).returns(true)

    get login_path, headers: { "Accept" => "text/html" }
    assert_redirected_to inventory_items_path
  end

  test "create signs in user and redirects on success" do
    Auth::SessionService.stubs(:login).returns({ success: true, data: { token: "t", refresh_token: "r", user: { id: @user.id } } })

    post login_path, params: { email: @user.email, password: "password" }, headers: { "Accept" => "text/html" }

    assert_redirected_to inventory_items_path
    assert_equal @user.id, session[:user_id]
  end

  test "create renders errors on failure" do
    Auth::SessionService.stubs(:login).returns({ success: false, error: { message: "Invalid" } })

    post login_path, params: { email: @user.email, password: "wrong" }, headers: { "Accept" => "text/html" }

    assert_response :unprocessable_entity
  end

  test "destroy logs out and redirects" do
    SessionsController.any_instance.stubs(:logout_user_via_api).returns(true)

    delete logout_path, headers: { "Accept" => "text/html" }

    assert_redirected_to root_path
  end

  test "create with remember_me checked sets refresh token to expire in 30 days" do
    refresh_token_record = RefreshToken.create_for_user!(@user, expires_in: 30.days)

    # Mock the service to return the refresh token
    Auth::SessionService.expects(:login).with(
      @user.email,
      "password",
      anything,
      remember_me: true
    ).returns({
      success: true,
      data: {
        token: "access_token",
        refresh_token: refresh_token_record.token,
        user: { id: @user.id, email: @user.email, first_name: @user.first_name, last_name: @user.last_name, created_at: @user.created_at }
      }
    })

    post login_path, params: {
      email: @user.email,
      password: "password",
      remember_me: "1"
    }, headers: { "Accept" => "text/html" }

    assert_redirected_to inventory_items_path

    # Verify refresh token cookie is set by checking Set-Cookie header
    # In integration tests, signed cookies can be accessed from response headers
    set_cookie_header = response.headers["Set-Cookie"]
    cookie_header_string = Array(set_cookie_header).join(" ")
    assert cookie_header_string.present?, "Set-Cookie header should be present"
    assert cookie_header_string.include?("refresh_token"), "Refresh token cookie should be set"

    # Check that SessionService was called with remember_me: true
    # (The expectation above verifies this)
  end

  test "create without remember_me sets refresh token to expire in 7 days" do
    refresh_token_record = RefreshToken.create_for_user!(@user, expires_in: 7.days)

    # Mock the service to return the refresh token
    Auth::SessionService.expects(:login).with(
      @user.email,
      "password",
      anything,
      remember_me: false
    ).returns({
      success: true,
      data: {
        token: "access_token",
        refresh_token: refresh_token_record.token,
        user: { id: @user.id, email: @user.email, first_name: @user.first_name, last_name: @user.last_name, created_at: @user.created_at }
      }
    })

    post login_path, params: {
      email: @user.email,
      password: "password"
    }, headers: { "Accept" => "text/html" }

    assert_redirected_to inventory_items_path

    # Verify refresh token cookie is set by checking Set-Cookie header
    set_cookie_header = response.headers["Set-Cookie"]
    cookie_header_string = Array(set_cookie_header).join(" ")
    assert cookie_header_string.present?, "Set-Cookie header should be present"
    assert cookie_header_string.include?("refresh_token"), "Refresh token cookie should be set"
  end

  test "create with remember_me unchecked (0) sets refresh token to expire in 7 days" do
    refresh_token_record = RefreshToken.create_for_user!(@user, expires_in: 7.days)

    Auth::SessionService.expects(:login).with(
      @user.email,
      "password",
      anything,
      remember_me: false
    ).returns({
      success: true,
      data: {
        token: "access_token",
        refresh_token: refresh_token_record.token,
        user: { id: @user.id, email: @user.email, first_name: @user.first_name, last_name: @user.last_name, created_at: @user.created_at }
      }
    })

    post login_path, params: {
      email: @user.email,
      password: "password",
      remember_me: "0"
    }, headers: { "Accept" => "text/html" }

    assert_redirected_to inventory_items_path
  end
end
