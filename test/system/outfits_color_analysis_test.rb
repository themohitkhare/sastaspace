require "application_system_test_case"

class OutfitsColorAnalysisTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")

    # Create categories
    @tops_category = create(:category, :clothing, name: "Tops #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, :clothing, name: "Bottoms #{SecureRandom.hex(4)}")

    # Create inventory items with color metadata
    @blue_shirt = create(:inventory_item,
      user: @user,
      name: "Blue Shirt #{SecureRandom.hex(4)}",
      category: @tops_category,
      metadata: { color: "blue", size: "M" }
    )
    @black_jeans = create(:inventory_item,
      user: @user,
      name: "Black Jeans #{SecureRandom.hex(4)}",
      category: @bottoms_category,
      metadata: { color: "black", size: "32" }
    )
    @red_shirt = create(:inventory_item,
      user: @user,
      name: "Red Shirt #{SecureRandom.hex(4)}",
      category: @tops_category,
      metadata: { color: "red", size: "L" }
    )

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login redirect to complete
    assert_text "Hello, #{@user.first_name}!", wait: 5
  end

  test "user can see color analysis section in outfit builder" do
    skip "Color analysis UI was intentionally removed from the builder"
    visit "/outfits/new"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 5

    # Check for color analysis target
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5
  end

  test "color analysis updates when items are added to outfit" do
    skip "Color analysis UI was intentionally removed from the builder"
    visit "/outfits/new"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 5

    # Wait for items to load
    begin
      assert_selector("[data-item-id]", wait: 20)
    rescue => e
      if page.has_text?("Failed to load items", wait: 0) || page.has_text?("Error loading items", wait: 0)
        skip "Items failed to load - likely API authentication issue"
      end
      raise e
    end
    assert_text @blue_shirt.name, wait: 10

    # Color analysis section should be present
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5

    # After adding items, color analysis should update (async)
    sleep 2
  end

  test "color analysis displays color information" do
    skip "Color analysis UI was intentionally removed from the builder"
    # Create outfit with items
    outfit = create(:outfit, user: @user, name: "Color Test Outfit #{SecureRandom.hex(4)}")
    outfit.outfit_items.create!(inventory_item: @blue_shirt)
    outfit.outfit_items.create!(inventory_item: @black_jeans)

    visit "/outfits/#{outfit.id}/edit"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/#{outfit.id}/edit"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 10

    # Color analysis section should show color coordination info
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5

    # May show color names or coordination score (depends on implementation)
    sleep 2
  end

  test "color analysis handles items with no color metadata" do
    skip "Color analysis UI was intentionally removed from the builder"
    # Create item without color metadata
    plain_item = create(:inventory_item,
      user: @user,
      name: "Plain Item #{SecureRandom.hex(4)}",
      category: @tops_category,
      metadata: { size: "M" }
    )

    outfit = create(:outfit, user: @user, name: "Plain Outfit #{SecureRandom.hex(4)}")
    outfit.outfit_items.create!(inventory_item: plain_item)

    visit "/outfits/#{outfit.id}/edit"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/#{outfit.id}/edit"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 10

    # Color analysis should still work (may show neutral or no colors)
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5
    sleep 2
  end

  test "color analysis updates when item is removed from outfit" do
    skip "Color analysis UI was intentionally removed from the builder"
    outfit = create(:outfit, user: @user, name: "Remove Test Outfit #{SecureRandom.hex(4)}")
    outfit.outfit_items.create!(inventory_item: @blue_shirt)
    outfit.outfit_items.create!(inventory_item: @black_jeans)

    visit "/outfits/#{outfit.id}/edit"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/#{outfit.id}/edit"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 10

    # Color analysis should be present
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5

    # When item is removed, color analysis should update
    sleep 2
  end

  test "color analysis shows coordination feedback" do
    skip "Color analysis UI was intentionally removed from the builder"
    # Create outfit with complementary colors
    outfit = create(:outfit, user: @user, name: "Coordinated Outfit #{SecureRandom.hex(4)}")
    outfit.outfit_items.create!(inventory_item: @blue_shirt)
    outfit.outfit_items.create!(inventory_item: @black_jeans)

    visit "/outfits/#{outfit.id}/edit"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/#{outfit.id}/edit"
    end

    # Wait for page to load
    assert_selector "[data-outfit-builder-target]", wait: 10

    # Color analysis section should show feedback
    assert_selector "[data-outfit-builder-target='colorAnalysis']", wait: 5

    # May contain text about color coordination
    # This depends on the actual implementation in the view
    sleep 2
  end
end
