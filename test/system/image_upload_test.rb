require "application_system_test_case"

class ImageUploadTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, email: "test@example.com", password: "Password123!")
    @category = create(:category, :clothing, name: "Tops")

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "user can upload primary image when creating item" do
    visit "/inventory_items/new"

    fill_in "Name", with: "Blue Shirt"
    select "Tops", from: "Category"
    select "clothing", from: "Item Type"

    # Upload image
    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "Primary Image", image_path

    click_button "Create Item"

    assert_text "Item created successfully"
    item = InventoryItem.find_by(name: "Blue Shirt")
    assert item.primary_image.attached?, "Primary image should be attached"
  end

  test "user can upload additional images when creating item" do
    visit "/inventory_items/new"

    fill_in "Name", with: "Red Dress"
    select "Tops", from: "Category"
    select "clothing", from: "Item Type"

    # Upload primary image
    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "Primary Image", image_path

    # Upload additional images
    attach_file "Additional Images", [ image_path, image_path ]

    click_button "Create Item"

    assert_text "Item created successfully"
    item = InventoryItem.find_by(name: "Red Dress")
    assert item.additional_images.count >= 2, "Should have at least 2 additional images"
  end

  test "user can add image to existing item" do
    item = create(:inventory_item, user: @user, name: "Yellow Sweater", category: @category)

    visit "/inventory_items/#{item.id}"
    click_on "Add Image"

    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "Primary Image", image_path
    click_button "Upload Image"

    assert_text "Image uploaded successfully"
    assert item.reload.primary_image.attached?, "Primary image should be attached"
  end

  test "user sees image preview after upload" do
    visit "/inventory_items/new"

    fill_in "Name", with: "Pink T-Shirt"
    select "Tops", from: "Category"
    select "clothing", from: "Item Type"

    image_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")
    attach_file "Primary Image", image_path

    # Should show preview before submitting
    assert_selector "img[alt='Image preview']", wait: 2

    click_button "Create Item"
    assert_text "Pink T-Shirt"
  end
end
