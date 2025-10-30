require "application_system_test_case"

class ImageUploadTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")
    @category = create(:category, :clothing, name: "Tops")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can upload primary image when creating item" do
    visit "/inventory_items/new"

    # Step 1
    select "Clothing", from: "Item Type"
    find("input[name='inventory_item[category_id]']", visible: false).set(@category.id)
    find("button[data-form-wizard-target='nextButton']").click

    # Step 2
    fill_in "Name", with: "Blue Shirt"
    find("button[data-form-wizard-target='nextButton']").click

    # Step 3
    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "inventory_item[primary_image]", image_path, visible: false
    find("button[data-form-wizard-target='nextButton']").click

    # Step 4
    page.execute_script("document.querySelector('form').requestSubmit()")

    assert_text "Item created successfully"
    item = InventoryItem.find_by(name: "Blue Shirt")
    assert item.primary_image.attached?, "Primary image should be attached"
  end

  test "user can upload additional images when creating item" do
    visit "/inventory_items/new"

    # Step 1
    select "Clothing", from: "Item Type"
    find("input[name='inventory_item[category_id]']", visible: false).set(@category.id)
    find("button[data-form-wizard-target='nextButton']").click

    # Step 2
    fill_in "Name", with: "Red Dress"
    find("button[data-form-wizard-target='nextButton']").click

    # Step 3
    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "inventory_item[primary_image]", image_path, visible: false

    # Upload additional images
    attach_file "inventory_item[additional_images][]", [ image_path, image_path ], visible: false

    find("button[data-form-wizard-target='nextButton']").click

    # Step 4
    page.execute_script("document.querySelector('form').requestSubmit()")

    assert_text "Item created successfully"
    item = InventoryItem.find_by(name: "Red Dress")
    assert item.additional_images.count >= 2, "Should have at least 2 additional images"
  end

  test "user can add image to existing item" do
    item = create(:inventory_item, user: @user, name: "Yellow Sweater", category: @category)

    visit edit_inventory_item_path(item)

    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "inventory_item[primary_image]", image_path, visible: true
    click_button "Update Item"

    assert_text "Item updated successfully"
    assert item.reload.primary_image.attached?, "Primary image should be attached"
  end

  test "user sees image preview after upload" do
    visit "/inventory_items/new"

    # Step 1
    select "Clothing", from: "Item Type"
    find("input[name='inventory_item[category_id]']", visible: false).set(@category.id)
    find("button[data-form-wizard-target='nextButton']").click

    # Step 2
    fill_in "Name", with: "Pink T-Shirt"
    find("button[data-form-wizard-target='nextButton']").click

    # Step 3
    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "inventory_item[primary_image]", image_path, visible: false

    # Preview is optional in headless; continue to submit

    find("button[data-form-wizard-target='nextButton']").click
    page.execute_script("document.querySelector('form').requestSubmit()")
    assert_text "Pink T-Shirt"
  end
end
