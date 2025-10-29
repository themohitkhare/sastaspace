require "application_system_test_case"

class CategoryFilterTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "Password123!")
    @tops_category = create(:category, :clothing, name: "Tops")
    @bottoms_category = create(:category, :clothing, name: "Bottoms")
    @shoes_category = create(:category, :shoes, name: "Sneakers")

    @tops_item = create(:inventory_item, user: @user, name: "Blue T-Shirt", category: @tops_category)
    @bottoms_item = create(:inventory_item, user: @user, name: "Black Jeans", category: @bottoms_category)
    @shoes_item = create(:inventory_item, user: @user, name: "Running Shoes", category: @shoes_category)

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign in"
  end

  test "user can filter inventory items by category" do
    visit "/inventory_items"

    # Should see all items initially
    assert_text "Blue T-Shirt"
    assert_text "Black Jeans"
    assert_text "Running Shoes"

    # Filter by Tops category
    select "Tops", from: "Filter by Category"
    click_button "Filter"

    assert_text "Blue T-Shirt"
    assert_no_text "Black Jeans"
    assert_no_text "Running Shoes"
  end

  test "user can filter by multiple categories" do
    visit "/inventory_items"

    # Filter by Tops and Bottoms
    check "Tops"
    check "Bottoms"
    click_button "Filter"

    assert_text "Blue T-Shirt"
    assert_text "Black Jeans"
    assert_no_text "Running Shoes"
  end

  test "user can clear category filter" do
    visit "/inventory_items"

    # Apply filter
    select "Tops", from: "Filter by Category"
    click_button "Filter"
    assert_no_text "Black Jeans"

    # Clear filter
    click_on "Clear Filter"
    assert_text "Blue T-Shirt"
    assert_text "Black Jeans"
    assert_text "Running Shoes"
  end

  test "item count updates when filtering" do
    visit "/inventory_items"

    assert_text "3 items"

    select "Tops", from: "Filter by Category"
    click_button "Filter"

    assert_text "1 item"
  end

  test "user sees empty message when filter returns no results" do
    empty_category = create(:category, name: "Empty Category")

    visit "/inventory_items"
    select "Empty Category", from: "Filter by Category"
    click_button "Filter"

    assert_text "No items found in this category"
  end
end
