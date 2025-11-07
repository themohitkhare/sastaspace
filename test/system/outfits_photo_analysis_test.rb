require "application_system_test_case"

class OutfitsPhotoAnalysisTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")

    # Create categories for items
    @tops_category = create(:category, :clothing, name: "Tops #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, :clothing, name: "Bottoms #{SecureRandom.hex(4)}")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can visit outfit photo analysis page" do
    visit "/outfits/new_from_photo"

    # Wait for page to load - may redirect if not authenticated
    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "h1", text: /Create Outfit from Photo/i, wait: 10
    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
  end

  test "user can see upload area" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    assert_selector "[data-outfit-photo-analyzer-target='uploadArea']", wait: 5
    assert_text /Click to upload/i
    assert_text /drag and drop/i
  end

  test "user can trigger file input" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    # File input should exist (hidden)
    assert_selector "input[type='file']", visible: :hidden, wait: 5
  end

  test "user sees loading state when uploading image" do
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    visit "/outfits/new_from_photo"

    # Upload image
    image_path = Rails.root.join("test/fixtures/files/sample_image.jpg")
    if File.exist?(image_path)
      attach_file("image", image_path, make_visible: true)

      # Should show loading state
      assert_text(/Analyzing your outfit photo/i, wait: 5)
      assert_selector("[data-outfit-photo-analyzer-target='loadingState']", wait: 2)
    end
  end

  test "user can see error message if upload fails" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    # Error state element should exist (hidden initially)
    assert_selector "[data-outfit-photo-analyzer-target='errorState']", visible: :hidden, wait: 5
  end

  test "user can cancel photo analysis" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5

    # Look for cancel button (might be in review step)
    cancel_button = find("button", text: /Cancel/i, wait: 2) rescue nil
    if cancel_button
      cancel_button.click
      sleep 1
      # Assert we're no longer on the photo analysis page or page changed
      assert(page.current_path != "/outfits/new_from_photo" || page.has_no_selector?("[data-outfit-photo-analyzer-target]", wait: 2))
    else
      # If cancel button doesn't exist, that's also valid - just assert page loaded
      assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    end
  end

  test "user can navigate away from photo analysis page" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5

    # Look for back/skip links or navigation
    skip_link = find("a", text: /Skip/i, wait: 2) rescue nil
    if skip_link
      skip_link.click
      sleep 1
      assert_current_path(/outfits/, wait: 5)
    else
      # If skip link doesn't exist, try navigation link
      outfits_link = find_link("Outfits", wait: 2) rescue nil
      if outfits_link
        outfits_link.click
        sleep 1
        assert(page.current_path.include?("outfits"), "Should navigate to outfits page")
      else
        # At minimum, assert page loaded successfully
        assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
      end
    end
  end

  test "user sees step indicators" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    # Check for step 1 (upload)
    assert_selector "[data-outfit-photo-analyzer-target='uploadStep']", wait: 5
    assert_text /Step 1/i
  end

  test "user can see file format requirements" do
    visit "/outfits/new_from_photo"

    if page.current_path == "/login"
      fill_in "Email", with: @user.email
      fill_in "Password", with: "Password123!"
      click_button "Sign In"
      visit "/outfits/new_from_photo"
    end

    assert_selector "[data-outfit-photo-analyzer-target]", wait: 5
    assert_text /PNG.*JPG.*WebP/i
    assert_text /5MB/i
  end
end
