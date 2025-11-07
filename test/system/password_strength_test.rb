require "application_system_test_case"

class PasswordStrengthTest < ApplicationSystemTestCase
  test "registration form validates password strength" do
    visit "/register"

    fill_in "Email", with: "test@example.com"
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "weak" # Too short
    fill_in "Confirm Password", with: "weak"

    click_button "Create Account"

    # Should show validation error
    assert_current_path "/register"
    assert_text(/password/i, wait: 2)
  end

  test "registration form accepts strong password" do
    visit "/register"

    fill_in "Email", with: "strong@example.com"
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "StrongPass123"
    fill_in "Confirm Password", with: "StrongPass123"

    click_button "Create Account"

    # Should succeed with strong password
    assert_current_path "/inventory_items", wait: 5
  end

  test "registration form rejects password without uppercase" do
    visit "/register"

    fill_in "Email", with: "noupper@example.com"
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "lowercase123"
    fill_in "Confirm Password", with: "lowercase123"

    click_button "Create Account"

    # Should show validation error
    assert_current_path "/register"
  end

  test "registration form rejects password without number" do
    visit "/register"

    fill_in "Email", with: "nonumber@example.com"
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "NoNumbers"
    fill_in "Confirm Password", with: "NoNumbers"

    click_button "Create Account"

    # Should show validation error
    assert_current_path "/register"
  end
end
