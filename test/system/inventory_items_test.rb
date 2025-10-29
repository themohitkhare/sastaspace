require "application_system_test_case"

class InventoryItemsTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "Password123!")
    @category = create(:category, :clothing, name: "Tops")
    @category2 = create(:category, :clothing, name: "Bottoms")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign in"
  end

  test "user can view list of inventory items" do
    item1 = create(:inventory_item, user: @user, name: "Blue T-Shirt", category: @category)
    item2 = create(:inventory_item, user: @user, name: "Black Jeans", category: @category2)

    visit "/inventory_items"

    assert_text "Blue T-Shirt"
    assert_text "Black Jeans"
    assert_text "Tops"
    assert_text "Bottoms"
  end

  test "user can see empty state when no items exist" do
    visit "/inventory_items"

    assert_text "You haven't added any items yet"
    assert_link "Add your first item", href: "/inventory_items/new"
  end

  test "user can navigate to create new inventory item page" do
    visit "/inventory_items"
    click_on "Add Item"

    assert_current_path "/inventory_items/new"
    assert_field "Name"
    assert_field "Category"
    assert_field "Item Type"
  end

  test "user can create a new inventory item" do
    visit "/inventory_items/new"

    fill_in "Name", with: "Red Sweater"
    select "Tops", from: "Category"
    select "clothing", from: "Item Type"
    fill_in "Description", with: "A cozy red sweater for winter"
    fill_in "Color", with: "Red"
    fill_in "Size", with: "M"
    click_button "Create Item"

    assert_text "Item created successfully"
    assert_text "Red Sweater"
    assert_current_path "/inventory_items"
  end

  test "user sees validation errors when creating item with invalid data" do
    visit "/inventory_items/new"

    click_button "Create Item"

    assert_text "Name can't be blank"
    assert_text "Category can't be blank"
  end

  test "user can view details of an inventory item" do
    item = create(:inventory_item, user: @user, name: "Green Jacket", category: @category, description: "A nice jacket")

    visit "/inventory_items"
    click_on "Green Jacket"

    assert_current_path "/inventory_items/#{item.id}"
    assert_text "Green Jacket"
    assert_text "A nice jacket"
  end
end

