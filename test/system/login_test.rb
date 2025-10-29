require "application_system_test_case"

class LoginTest < ApplicationSystemTestCase
  test "user can login with valid credentials" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    visit root_path
    click_on "Login"

    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign in"

    assert_text "Welcome back, #{user.first_name}"
    assert_current_path "/inventory_items"
  end

  test "user cannot login with invalid credentials" do
    visit root_path
    click_on "Login"

    fill_in "Email", with: "wrong@example.com"
    fill_in "Password", with: "WrongPassword123!"
    click_button "Sign in"

    assert_text "Invalid email or password"
    assert_current_path "/login"
  end

  test "user is redirected to inventory after successful login" do
    user = create(:user, email: "test@example.com", password: "Password123!")

    visit "/inventory_items"
    # Should redirect to login when not authenticated
    assert_current_path "/login"

    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign in"

    assert_current_path "/inventory_items"
  end
end

