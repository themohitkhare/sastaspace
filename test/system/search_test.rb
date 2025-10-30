require "application_system_test_case"

class SearchTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")
    @category = create(:category, :clothing)

    @red_shirt = create(:inventory_item, user: @user, name: "Red T-Shirt", category: @category, description: "A bright red shirt")
    @blue_shirt = create(:inventory_item, user: @user, name: "Blue T-Shirt", category: @category, description: "A cool blue shirt")
    @black_pants = create(:inventory_item, user: @user, name: "Black Pants", category: @category, description: "Formal black pants")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can search inventory items by name" do
    visit "/inventory_items"

    fill_in "Search", with: "Red"
    sleep 1.0

    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user can search inventory items by description" do
    visit "/inventory_items"

    fill_in "Search", with: "bright"
    sleep 1.0

    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
  end

  test "user can search with multiple keywords" do
    visit "/inventory_items"

    fill_in "Search", with: "T-Shirt"
    sleep 1.0

    assert_text "Red T-Shirt"
    assert_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user sees empty results message when search returns nothing" do
    visit "/inventory_items"

    fill_in "Search", with: "NonExistentItem123"
    sleep 1.0

    assert_text "No items found"
    assert_no_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user can clear search and see all items" do
    visit "/inventory_items"

    # Apply search
    fill_in "Search", with: "Red"
    sleep 1.0
    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"

    # Clear search
    fill_in "Search", with: ""
    find_field("Search").send_keys(:enter)
    sleep 1.0

    # Or use clear filters if available
    if page.has_link?("Clear Filters", wait: 1)
      click_on "Clear Filters"
      sleep 1.0
    end

    assert_text "Red T-Shirt"
    assert_text "Blue T-Shirt"
    assert_text "Black Pants"
  end

  test "search works with category filter combined" do
    bottoms_category = create(:category, :clothing)
    blue_pants = create(:inventory_item, user: @user, name: "Blue Jeans", category: bottoms_category)

    visit "/inventory_items"

    # Filter by selected category (auto-submits)
    select @category.name, from: "Category"
    sleep 1.0

    # Then search
    fill_in "Search", with: "Blue"
    sleep 1.0

    assert_text "Blue T-Shirt"
    assert_no_text "Blue Jeans" # Should be filtered out by category
  end
end
