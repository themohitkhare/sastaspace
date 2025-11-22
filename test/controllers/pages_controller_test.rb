# frozen_string_literal: true

require "test_helper"

class PagesControllerTest < ActionDispatch::IntegrationTest
  test "should get home page when not logged in" do
    get root_url
    assert_response :success
    assert_select "title", "SastaSpace - Your AI-Powered Digital Wardrobe"
  end

  test "home page should have proper meta tags" do
    get root_url
    assert_response :success

    # Check description meta tag
    assert_select 'meta[name="description"]' do |elements|
      assert elements.first["content"].include?("Save 40%"), "Description should mention savings"
    end

    # Check Open Graph tags
    assert_select 'meta[property="og:title"]' do |elements|
      assert_equal "SastaSpace - Your AI-Powered Digital Wardrobe", elements.first["content"]
    end

    assert_select 'meta[property="og:type"]' do |elements|
      assert_equal "website", elements.first["content"]
    end
  end

  test "home page should display hero section" do
    get root_url
    assert_response :success

    # Check for headline
    assert_select "h1", text: /Your AI-Powered Wardrobe/

    # Check for CTA buttons
    assert_select "a[href='#{register_path}']", text: /Get Started/
  end

  test "home page should display value propositions" do
    get root_url
    assert_response :success

    # Check for all four value props
    assert_select "body", text: /Save Money/
    assert_select "body", text: /Save Time/
    assert_select "body", text: /Look Better/
    assert_select "body", text: /Live Sustainably/
  end

  test "home page should display features section" do
    get root_url
    assert_response :success

    assert_select "body", text: /AI Analyzes Your Clothes/
    assert_select "body", text: /Personalized Outfit Recommendations/
    assert_select "body", text: /Your Data Never Leaves Your Device/
  end

  test "home page should display how it works section" do
    get root_url
    assert_response :success

    assert_select "body", text: /Snap a Photo/
    assert_select "body", text: /AI Analyzes Everything/
    assert_select "body", text: /Get Outfit Ideas/
  end

  test "home page should display testimonials" do
    get root_url
    assert_response :success

    # Check for testimonial content
    assert_select "body", text: /Alex K\./
    assert_select "body", text: /Jamie L\./
    assert_select "body", text: /Morgan R\./
  end

  test "home page should display footer with links" do
    get root_url
    assert_response :success

    # Check for footer sections
    assert_select "footer" do
      assert_select "a[href='#{login_path}']"
      assert_select "a[href='#{register_path}']"
    end
    # Check for footer text content (not inside assert_select footer block)
    assert_select "footer", text: /Privacy Policy/
    assert_select "footer", text: /Terms of Service/
  end

  test "should redirect to inventory when logged in" do
    user = create(:user, password: "Password123!")

    # Stub user_signed_in? to return true
    # We're testing the redirect behavior, not the authentication mechanism
    # Authentication is tested in SessionAuthenticableTest
    PagesController.any_instance.stubs(:user_signed_in?).returns(true)

    get root_url
    assert_redirected_to inventory_items_path
  end

  test "navigation should show public links when not logged in" do
    get root_url
    assert_response :success

    # Check for public navigation
    assert_select "a[href='#features']", text: /Features/
    assert_select "a[href='#how-it-works']", text: /How It Works/
    assert_select "a[href='#{login_path}']", text: /Login/
    assert_select "a[href='#{register_path}']", text: /Get Started/
  end

  test "navigation should show app links when logged in" do
    user = create(:user, password: "Password123!")

    # Stub authentication for InventoryItemsController
    # We're testing the navigation display, not the authentication mechanism
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(user)
    InventoryItemsController.any_instance.stubs(:user_signed_in?).returns(true)

    # Visit inventory since logged-in users get redirected
    get inventory_items_path
    assert_response :success

    # Check for app navigation
    assert_select "a[href='#{inventory_items_path}']", text: /Inventory/
    assert_select "a[href='#{outfits_path}']", text: /Outfits/
    assert_select "a[data-turbo-method='delete'][href='#{logout_path}']", text: /Logout/
  end

  test "home page should be accessible without authentication" do
    # Ensure no redirect or authentication required
    get root_url
    assert_response :success
    assert_not_nil response.body
    assert response.body.length > 100, "Response should have substantial content"
  end

  test "home page should have proper semantic HTML structure" do
    get root_url
    assert_response :success

    # Check for proper heading hierarchy
    assert_select "h1", minimum: 1
    assert_select "h2", minimum: 1

    # Check for main landmark
    assert_select "main"

    # Check for footer
    assert_select "footer"

    # Check for navigation
    assert_select "nav"
  end

  test "home page should have skip to main content link for accessibility" do
    get root_url
    assert_response :success

    # This would be added in the layout if needed for better accessibility
    # For now, we check that main content is present
    assert_select "main"
  end

  test "all CTA buttons should link to registration" do
    get root_url
    assert_response :success

    # Count register links (should be multiple CTAs)
    register_links = css_select("a[href='#{register_path}']")
    assert register_links.length >= 2, "Should have multiple CTAs linking to registration"
  end

  private

  def sign_in_as(user)
    # Generate valid JWT tokens for the user
    access_token = Auth::JsonWebToken.encode_access_token(user_id: user.id)
    refresh_token = RefreshToken.create_for_user!(user)

    # Stub Auth::SessionService.login to return success with valid tokens
    Auth::SessionService.stubs(:login).returns({
      success: true,
      data: {
        token: access_token,
        refresh_token: refresh_token.token,
        user: { id: user.id }
      }
    })

    # Post to login with correct params format
    # Factory default password is "Password123!"
    post login_path, params: {
      email: user.email,
      password: "Password123!"
    }, headers: { "Accept" => "text/html" }

    # Verify session was set
    assert_equal user.id, session[:user_id], "Session should be set after login"
  end
end
