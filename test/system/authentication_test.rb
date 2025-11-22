require "application_system_test_case"

class AuthenticationTest < ApplicationSystemTestCase
  # Registration Flow Tests
  test "user can register with valid credentials" do
    visit "/register"

    fill_in "Email", with: "newuser@example.com"
    fill_in "First Name", with: "John"
    fill_in "Last Name", with: "Doe"
    fill_in "Password", with: "SecurePass123!"
    fill_in "Confirm Password", with: "SecurePass123!"

    click_button "Create Account"

    # Wait for redirect and check success message
    assert_text "Welcome, John! Your account has been created.", wait: 5
    assert_current_path "/inventory_items"

    # Verify user is logged in by checking navigation
    assert_text "Hello, John!"
  end

  test "registration form validates required fields" do
    visit "/register"

    click_button "Create Account"

    # Should stay on registration page with validation errors
    assert_current_path "/register"
  end

  test "registration form validates password confirmation match" do
    visit "/register"

    fill_in "Email", with: "test@example.com"
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "SecurePass123!"
    fill_in "Confirm Password", with: "DifferentPass123!"

    click_button "Create Account"

    # Should show validation error and stay on page
    assert_current_path "/register"
  end

  test "registration form shows error for duplicate email" do
    existing_user = create(:user, email: "existing@example.com")

    visit "/register"

    fill_in "Email", with: existing_user.email
    fill_in "First Name", with: "Test"
    fill_in "Last Name", with: "User"
    fill_in "Password", with: "SecurePass123!"
    fill_in "Confirm Password", with: "SecurePass123!"

    click_button "Create Account"

    # Should show validation error
    assert_current_path "/register"
    assert_text(/already been taken|creation failed/i)
  end

  test "registration redirects logged-in users to inventory" do
    user = create(:user)

    # Login first
    visit "/login"
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Try to access registration
    visit "/register"

    assert_current_path "/inventory_items"
  end

  # Login Flow Tests
  test "user can login with valid credentials" do
    user = create(:user, password: "Password123!")

    visit "/login"

    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    assert_text "Welcome back, #{user.first_name}!", wait: 5
    assert_current_path "/inventory_items"
    assert_text "Hello, #{user.first_name}!"
  end

  test "login form shows error for invalid credentials" do
    visit "/login"

    fill_in "Email", with: "wrong@example.com"
    fill_in "Password", with: "WrongPassword123!"
    click_button "Sign In"

    assert_text(/invalid email or password/i, wait: 2)
    assert_current_path "/login"
  end

  test "login form has remember me checkbox" do
    visit "/login"

    assert_field "Remember me", type: :checkbox
  end

  test "login redirects already logged-in users to inventory" do
    user = create(:user)

    visit "/login"
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Try to access login again
    visit "/login"

    assert_current_path "/inventory_items"
  end

  test "login form has forgot password link" do
    visit "/login"

    assert_link "Forgot password?"
  end

  # Logout Flow Tests
  test "user can logout successfully" do
    user = create(:user, password: "Password123!")

    # Login first
    visit "/login"
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    assert_text "Hello, #{user.first_name}!", wait: 2

    # Dismiss any overlapping flash
    if page.has_css?("button[aria-label='Dismiss']", wait: 0.5)
      first("button[aria-label='Dismiss']").click
    end
    # Logout
    click_link "Logout"

    # Flash may be transient; verify we returned to public state
    # Logout redirects to root_path (home page) which is public
    assert_current_path "/"
    assert_link "Login"
    assert_link "Register"
  end

  # Protected Routes Tests
  test "protected routes redirect to login when not authenticated" do
    visit "/inventory_items"

    assert_current_path "/login"
    assert_text(/Please sign in/i)
  end

  test "protected routes are accessible after login" do
    user = create(:user, password: "Password123!")

    visit "/inventory_items"

    # Should redirect to login
    assert_current_path "/login"

    # Login
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Should now access inventory
    assert_current_path "/inventory_items", wait: 5
  end

  # Navigation Tests
  test "navigation shows login and register when not authenticated" do
    visit "/"

    assert_link "Login"
    assert_link "Register"
    assert_no_text "Hello,"
    assert_no_link "Logout"
  end

  test "navigation shows user info and logout when authenticated" do
    user = create(:user, first_name: "Jane")

    visit "/login"
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    assert_text "Hello, Jane!", wait: 5
    assert_link "Logout"
    assert_link "Inventory"
    assert_no_link "Login"
    assert_no_link "Register"
  end

  # Session Persistence Tests
  test "user session persists across page navigations" do
    user = create(:user, first_name: "Alice")

    visit "/login"
    fill_in "Email", with: user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to different pages
    visit "/inventory_items"
    assert_text "Hello, Alice!", wait: 5

    visit "/"
    # Root shows inventory when logged in
    assert_selector "h1", text: "My Inventory"
    assert_text "Hello, Alice!"
  end

  test "login preserves email on failed attempt" do
    visit "/login"

    fill_in "Email", with: "test@example.com"
    fill_in "Password", with: "WrongPassword"
    click_button "Sign In"

    # Email should still be filled
    email_field = find_field("Email")
    assert_equal "test@example.com", email_field.value
  end

  # Integration Test: Full Registration and Login Flow
  test "complete registration to login flow works" do
    # Register
    visit "/register"

    fill_in "Email", with: "newuser@example.com"
    fill_in "First Name", with: "Bob"
    fill_in "Last Name", with: "Smith"
    fill_in "Password", with: "SecurePass123!"
    fill_in "Confirm Password", with: "SecurePass123!"

    click_button "Create Account"

    assert_text "Welcome, Bob! Your account has been created.", wait: 5
    assert_current_path "/inventory_items"

    # Dismiss any overlapping flash
    if page.has_css?("button[aria-label='Dismiss']", wait: 0.5)
      first("button[aria-label='Dismiss']").click
    end
    # Logout
    click_link "Logout"

    # Verify public state - logout redirects to root_path (home page)
    assert_current_path "/"

    # Login with same credentials
    visit "/login"
    fill_in "Email", with: "newuser@example.com"
    fill_in "Password", with: "SecurePass123!"
    click_button "Sign In"

    assert_text "Welcome back, Bob!", wait: 5
    assert_current_path "/inventory_items"
  end
end
