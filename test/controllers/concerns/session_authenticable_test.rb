require "test_helper"

class SessionAuthenticableTest < ActionDispatch::IntegrationTest
  # Test SessionAuthenticable through integration tests using SessionsController
  setup do
    @user = create(:user, password: "Password123", password_confirmation: "Password123")
  end

  test "get_current_user_from_session returns user when session exists" do
    post login_path, params: {
      email: @user.email,
      password: "Password123"
    }, headers: { "Accept" => "text/html" }

    # Stub authentication to succeed
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
end
