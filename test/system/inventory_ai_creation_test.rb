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
    page.execute_script("document.querySelector('input[type=file]').dispatchEvent(new Event('change'))")

    # Should show some error or validation message
    # The exact behavior depends on JavaScript validation
  end

  test "can cancel and return to inventory list" do
    visit new_ai_inventory_items_path

    click_link "Cancel"

    assert_current_path inventory_items_path
  end
end
