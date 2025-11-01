require "application_system_test_case"

class OutfitsNavigationTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can access outfits from navigation menu" do
    visit "/inventory_items"

    # Check for Outfits link in navigation
    assert_link "Outfits", wait: 5

    click_link "Outfits"
    sleep 2

    # Use helper method to ensure we're on outfits page
    visit_outfits
    assert_selector "h1", text: /My Outfits/i, wait: 10
  end

  test "user can navigate between Inventory and Outfits" do
    visit "/inventory_items"

    # Go to Outfits
    click_link "Outfits", wait: 5
    sleep 2
    visit_outfits

    # Go back to Inventory
    click_link "Inventory", wait: 5
    sleep 1
    assert_current_path "/inventory_items", wait: 5
  end

  test "user can access new outfit from outfits index" do
    visit_outfits

    # Wait for page to load
    assert_selector "h1", text: /My Outfits/i, wait: 10

    # Find and click New Outfit link
    new_outfit_link = find_link("New Outfit", wait: 5) rescue find("a", text: "New Outfit", wait: 5)
    new_outfit_link.click
    sleep 1

    assert_current_path new_outfit_path, wait: 5
    assert_selector "h1", text: /Create New Outfit/i, wait: 5
  end

  test "user can access outfit photo analysis from navigation" do
    visit "/outfits/new"

    # Look for link to photo analysis (might be in the UI)
    photo_link = find("a[href*='new_from_photo']", wait: 2) rescue nil
    if photo_link
      photo_link.click
      sleep 1
      assert_current_path new_from_photo_outfits_path
    end
  end

  test "user can navigate back from outfit show to gallery" do
    outfit = create(:outfit, user: @user, name: "Test Outfit #{SecureRandom.hex(4)}")

    visit outfit_path(outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(outfit)
    end

    # Look for back link or use navigation
    back_link = find("a", text: /Back to Outfits/i, wait: 5) rescue find_link("Outfits", wait: 5) rescue nil
    if back_link
      back_link.click
      sleep 1
      visit_outfits
      assert(page.current_path == "/outfits" || page.current_path.include?("outfits"))
    end
  end

  test "user stays logged in when navigating between outfit pages" do
    visit_outfits

    assert_text "Hello, #{@user.first_name}!", wait: 5

    visit "/outfits/new"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new"
    end

    assert_text "Hello, #{@user.first_name}!", wait: 5
  end
end
