require "test_helper"

class RegistrationsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
  end

  test "new renders successfully when not signed in" do
    get register_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "new redirects when already signed in" do
    RegistrationsController.any_instance.stubs(:user_signed_in?).returns(true)
    get register_path, headers: { "Accept" => "text/html" }
    assert_redirected_to inventory_items_path
  end

  test "create registers user and redirects on success" do
    Auth::SessionService.stubs(:register).returns({ success: true, data: { token: "t", refresh_token: "r", user: { id: @user.id } } })

    post register_path, params: { user: { email: @user.email, first_name: @user.first_name, last_name: @user.last_name, password: "password", password_confirmation: "password" } }, headers: { "Accept" => "text/html" }

    assert_redirected_to inventory_items_path
    assert_equal @user.id, session[:user_id]
  end

  test "create renders errors on failure" do
    Auth::SessionService.stubs(:register).returns({ success: false, error: { message: "Invalid", details: { email: [ "taken" ] } } })

    post register_path, params: { user: { email: "bad", password: "short" } }, headers: { "Accept" => "text/html" }

    assert_response :unprocessable_entity
  end
end
