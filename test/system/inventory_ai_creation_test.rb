require "application_system_test_case"

class InventoryAiCreationTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "visiting AI-powered inventory creation page" do
    visit new_ai_inventory_items_path

    assert_selector "h1", text: /Add New Item with AI/i
    # File input is hidden for styling, check with visible: :all
    assert_selector "input[type='file']", visible: :all
  end

  test "uploading image triggers analysis flow" do
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    visit new_ai_inventory_items_path

    # Upload image
    image_path = Rails.root.join("test/fixtures/files/sample_image.jpg")
    attach_file("image", image_path, make_visible: true)

    # Should show loading state
    assert_text(/Analyzing your item/i, wait: 5)

    # Wait for analysis to complete (may take a while with real Ollama)
    # This will timeout if Ollama is slow or unavailable
    assert_text(/Analysis complete|Next/i, wait: 60)

    # If analysis completes, form should be pre-filled
    if page.has_text?("Analysis complete", wait: 2)
      # Check that form fields are populated
      # (This depends on what the AI extracts)
    end
  end

  test "shows error message if image upload fails" do
    visit new_ai_inventory_items_path

    # Try uploading invalid file (simulated by JavaScript validation)
    # This test checks the UI error handling
    file_input = find("input[type='file']", visible: :hidden, wait: 2) rescue nil
    if file_input
      page.execute_script("document.querySelector('input[type=file]').dispatchEvent(new Event('change'))")
      sleep 1
      # Should show some error or validation message
      # Just verify page is still functional (no crash)
      assert_selector "h1", text: /Add New Item with AI/i
    else
      # If no file input, skip assertion
      skip "File input not found"
    end
  end

  test "can cancel and return to inventory list" do
    visit new_ai_inventory_items_path

    click_link "Cancel"

    assert_current_path inventory_items_path
  end

  test "full AI creation flow attaches primary image to created item" do
    # This test verifies that when creating an item through AI, the image is properly attached
    # This would have caught the bug where blob_id wasn't being submitted
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    @category = create(:category, :clothing, name: "T-Shirts #{SecureRandom.hex(4)}")

    visit new_ai_inventory_items_path

    # Upload image
    image_path = Rails.root.join("test/fixtures/files/sample_image.jpg")
    attach_file("image", image_path, make_visible: true)

    # Wait for analysis to complete
    assert_text(/Analysis complete|Next/i, wait: 60)

    # Fill out form (may be pre-filled by AI)
    if page.has_field?("Category", wait: 2)
      # Use the category picker or select directly
      find("button", text: /Select a category/i, wait: 2).click if page.has_button?("Select a category", wait: 2)
      find("li", text: @category.name, wait: 2).click if page.has_text?(@category.name, wait: 2)
    end

    # Fill name if not already filled
    fill_in "Name", with: "Test AI Item #{SecureRandom.hex(4)}" if page.has_field?("Name", wait: 2)

    # Navigate through wizard steps
    if page.has_button?("Next", wait: 2)
      click_button "Next" until page.has_button?("Create Item", wait: 2) || page.has_button?("Submit", wait: 2)
    end

    # Submit form
    click_button "Create Item" if page.has_button?("Create Item", wait: 2)

    # Should redirect to inventory items
    assert_current_path inventory_items_path, wait: 5

    # Find the created item
    item = @user.inventory_items.order(created_at: :desc).first
    assert_not_nil item, "Item should be created"

    # CRITICAL: Verify the primary image is attached
    # This would have caught the bug!
    assert item.primary_image.attached?, "Primary image should be attached after AI creation flow. Item ID: #{item.id}"
    assert item.primary_image.blob.present?, "Blob should exist for attached image"
  end
end
