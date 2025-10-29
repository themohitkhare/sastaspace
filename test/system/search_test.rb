require "application_system_test_case"

class SearchTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "Password123!")
    @category = create(:category, :clothing, name: "Tops")

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
    click_button "Search"

    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user can search inventory items by description" do
    visit "/inventory_items"

    fill_in "Search", with: "bright"
    click_button "Search"

    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
  end

  test "user can search with multiple keywords" do
    visit "/inventory_items"

    fill_in "Search", with: "T-Shirt"
    click_button "Search"

    assert_text "Red T-Shirt"
    assert_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user sees empty results message when search returns nothing" do
    visit "/inventory_items"

    fill_in "Search", with: "NonExistentItem123"
    click_button "Search"

    assert_text "No items found matching"
    assert_no_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"
    assert_no_text "Black Pants"
  end

  test "user can clear search and see all items" do
    visit "/inventory_items"

    # Apply search
    fill_in "Search", with: "Red"
    click_button "Search"
    assert_text "Red T-Shirt"
    assert_no_text "Blue T-Shirt"

    # Clear search
    click_on "Clear"
    assert_text "Red T-Shirt"
    assert_text "Blue T-Shirt"
    assert_text "Black Pants"
  end

  test "search works with category filter combined" do
    bottoms_category = create(:category, :clothing, name: "Bottoms")
    blue_pants = create(:inventory_item, user: @user, name: "Blue Jeans", category: bottoms_category)

    visit "/inventory_items"

    # Filter by Tops category
    select "Tops", from: "Filter by Category"
    click_button "Filter"

    # Then search
    fill_in "Search", with: "Blue"
    click_button "Search"

    assert_text "Blue T-Shirt"
    assert_no_text "Blue Jeans" # Should be filtered out by category
  end
end
