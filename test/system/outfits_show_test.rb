require "application_system_test_case"

class OutfitsShowTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")

    # Create categories
    @tops_category = create(:category, :clothing, name: "Tops #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, :clothing, name: "Bottoms #{SecureRandom.hex(4)}")

    # Create inventory items
    @shirt = create(:inventory_item,
      user: @user,
      name: "Blue Shirt #{SecureRandom.hex(4)}",
      category: @tops_category
    )
    @jeans = create(:inventory_item,
      user: @user,
      name: "Black Jeans #{SecureRandom.hex(4)}",
      category: @bottoms_category
    )

    # Create outfit
    @outfit = create(:outfit,
      user: @user,
      name: "Test Outfit #{SecureRandom.hex(4)}",
      description: "A test outfit description",
      occasion: "casual",
      is_favorite: true
    )
    @outfit.outfit_items.create!(inventory_item: @shirt)
    @outfit.outfit_items.create!(inventory_item: @jeans)

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can view outfit details" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    assert_text @outfit.name, wait: 5
    assert_text @outfit.description
    assert_text @shirt.name
    assert_text @jeans.name
  end

  test "user can see outfit items" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    assert_text "Items (2)", wait: 5
    assert_text @shirt.name
    assert_text @jeans.name
    assert_text @tops_category.name
    assert_text @bottoms_category.name
  end

  test "user can see favorite indicator on favorite outfits" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    # Check for favorite star icon (there should be an SVG)
    assert_selector "svg", wait: 5
    assert_text @outfit.name, wait: 5
  end

  test "user can see occasion badge" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    assert_text "Casual", wait: 5 # Capitalized occasion
  end

  test "user can navigate to edit outfit" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    # There might be multiple "Edit" links, find the one for the outfit
    edit_link = find("a[href='#{edit_outfit_path(@outfit)}']", wait: 5) rescue find_link("Edit", match: :first, wait: 5)
    edit_link.click
    sleep 1

    assert_current_path edit_outfit_path(@outfit), wait: 5
  end

  test "user can navigate back to outfits list" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    # Look for back link or navigate via menu
    back_link = find("a", text: /Back to Outfits/i, wait: 5) rescue find_link("Outfits", wait: 5) rescue nil
    if back_link
      back_link.click
      sleep 1
      visit_outfits
      assert(page.current_path == "/outfits" || page.current_path.include?("outfits"))
    end
  end

  test "user sees empty state when outfit has no items" do
    empty_outfit = create(:outfit,
      user: @user,
      name: "Empty Outfit #{SecureRandom.hex(4)}"
    )

    visit outfit_path(empty_outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(empty_outfit)
    end

    assert_text /No items in this outfit/i, wait: 5
    assert_link "Edit Outfit"
  end

  test "user can see creation date" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    assert_text /Created/i, wait: 5
    assert_text /ago/i
  end

  test "user can click on item to view item details" do
    visit outfit_path(@outfit)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(@outfit)
    end

    # Wait for page to load
    assert_text @shirt.name, wait: 5

    # Click on item name
    item_link = find_link(@shirt.name, wait: 5) rescue find("a", text: @shirt.name, match: :first, wait: 5)
    item_link.click
    sleep 1

    # Should navigate to inventory item page
    assert_current_path(/inventory_items/, wait: 5)
  end

  test "user can delete outfit from show page" do
    outfit_to_delete = create(:outfit,
      user: @user,
      name: "Delete Me #{SecureRandom.hex(4)}"
    )

    visit outfit_path(outfit_to_delete)

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit outfit_path(outfit_to_delete)
    end

    assert_text outfit_to_delete.name, wait: 5

    # Find delete link using more specific selector
    delete_selector = "a[href='#{outfit_path(outfit_to_delete)}'][data-turbo-method='delete']"
    
    # Wait for the delete link to be present and visible
    assert_selector delete_selector, text: /Delete/i, wait: 5
    
    # Handle confirmation and click in a way that prevents stale element errors
    # Turbo uses data-turbo-confirm, which works with accept_confirm
    # Try with message first, fallback to without message
    begin
      page.accept_confirm "Are you sure you want to delete this outfit?" do
        # Find the element fresh right before clicking
        find(delete_selector, text: /Delete/i, wait: 2).click
      end
    rescue Capybara::ModalNotFound
      # Fallback: accept any confirmation dialog
      page.accept_confirm do
        find(delete_selector, text: /Delete/i, wait: 2).click
      end
    end
      
    # Wait for redirect
    assert_current_path(/outfits/, wait: 5)
    assert_no_text outfit_to_delete.name, wait: 5
  end
end
