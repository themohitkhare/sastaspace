require "application_system_test_case"

class LoginTest < ApplicationSystemTestCase
  test "user can login with valid credentials" do
    user = create(:user, password: "Password123!")

    visit "/login"

    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    assert_text "Welcome back, #{user.first_name}"
    assert_current_path "/inventory_items"
  end

  test "user cannot login with invalid credentials" do
    visit "/login"

    fill_in "Email", with: "wrong@example.com"
    fill_in "Password", with: "WrongPassword123!"
    click_button "Sign In"

    assert_text "Invalid email or password"
    assert_current_path "/login"
  end

  test "user is redirected to inventory after successful login" do
    user = create(:user, password: "Password123!")

    visit "/inventory_items"
    # Should redirect to login when not authenticated
    assert_current_path "/login"

    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    assert_current_path "/inventory_items"
  end
end
