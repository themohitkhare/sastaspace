require "test_helper"

class ApiV1ClothingItemsTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @other_user = create(:user)
    @other_token = generate_jwt_token(@other_user)
  end

  test "GET /api/v1/clothing_items returns user's clothing items" do
    item1 = create(:clothing_item, user: @user, name: "Blue Shirt")
    item2 = create(:clothing_item, user: @user, name: "Red Pants")
    other_item = create(:clothing_item, user: @other_user, name: "Other Item")

    get "/api/v1/clothing_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 2, body["data"]["items"].length, "Should return only user's items"
    item_names = body["data"]["items"].map { |item| item["name"] }
    assert_includes item_names, "Blue Shirt"
    assert_includes item_names, "Red Pants"
    assert_not_includes item_names, "Other Item"
  end

  test "GET /api/v1/clothing_items without auth returns 401" do
    get "/api/v1/clothing_items", headers: api_v1_headers

    assert_unauthorized_response
  end

  test "GET /api/v1/clothing_items with pagination" do
    # Create 25 items
    25.times { create(:clothing_item, user: @user) }

    get "/api/v1/clothing_items?page=1&per_page=10", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 10, body["data"]["items"].length, "Should return 10 items per page"
    assert body["data"]["pagination"].present?, "Should include pagination info"
    assert_equal 25, body["data"]["pagination"]["total_count"], "Should show total count"
    assert_equal 3, body["data"]["pagination"]["total_pages"], "Should calculate total pages"
  end

  test "GET /api/v1/clothing_items with category filter" do
    shirt = create(:clothing_item, user: @user, category: "top")
    pants = create(:clothing_item, user: @user, category: "bottom")

    get "/api/v1/clothing_items?category=top", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["items"].length, "Should return only tops"
    assert_equal "top", body["data"]["items"].first["category"]
  end

  test "GET /api/v1/clothing_items with season filter" do
    summer_item = create(:clothing_item, user: @user, season: "summer")
    winter_item = create(:clothing_item, user: @user, season: "winter")

    get "/api/v1/clothing_items?season=summer", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["items"].length, "Should return only summer items"
    assert_equal "summer", body["data"]["items"].first["season"]
  end

  test "GET /api/v1/clothing_items with search query" do
    blue_shirt = create(:clothing_item, user: @user, name: "Blue Cotton Shirt")
    red_pants = create(:clothing_item, user: @user, name: "Red Denim Pants")

    get "/api/v1/clothing_items?q=blue", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["items"].length, "Should return only matching items"
    assert_equal "Blue Cotton Shirt", body["data"]["items"].first["name"]
  end

  test "POST /api/v1/clothing_items creates new clothing item" do
    item_data = {
      name: "Test Shirt",
      category: "top",
      brand: "Test Brand",
      color: "blue",
      size: "M",
      season: "summer",
      occasion: "casual"
    }

    post "/api/v1/clothing_items", params: item_data, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["item"]["id"].present?, "Should return item ID"
    assert_equal item_data[:name], body["data"]["item"]["name"]
    assert_equal item_data[:category], body["data"]["item"]["category"]

    # Verify item was created
    item = ClothingItem.find(body["data"]["item"]["id"])
    assert_equal @user, item.user, "Should belong to current user"
  end

  test "POST /api/v1/clothing_items with invalid data returns validation errors" do
    invalid_data = {
      name: "",
      category: "invalid_category"
    }

    post "/api/v1/clothing_items", params: invalid_data, headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response

    assert body["error"]["details"].present?, "Expected validation error details"
    assert body["error"]["details"]["name"].present?, "Expected name validation error"
    assert body["error"]["details"]["category"].present?, "Expected category validation error"
  end

  test "GET /api/v1/clothing_items/:id returns specific clothing item" do
    item = create(:clothing_item, user: @user, name: "Test Item")

    get "/api/v1/clothing_items/#{item.id}", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal item.id, body["data"]["item"]["id"]
    assert_equal "Test Item", body["data"]["item"]["name"]
  end

  test "GET /api/v1/clothing_items/:id for other user's item returns 404" do
    other_item = create(:clothing_item, user: @other_user)

    get "/api/v1/clothing_items/#{other_item.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "PUT /api/v1/clothing_items/:id updates clothing item" do
    item = create(:clothing_item, user: @user, name: "Original Name")

    update_data = { name: "Updated Name", color: "red" }

    put "/api/v1/clothing_items/#{item.id}", params: update_data, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal "Updated Name", body["data"]["item"]["name"]
    assert_equal "red", body["data"]["item"]["color"]

    # Verify item was updated
    item.reload
    assert_equal "Updated Name", item.name
    assert_equal "red", item.color
  end

  test "PUT /api/v1/clothing_items/:id for other user's item returns 404" do
    other_item = create(:clothing_item, user: @other_user)

    update_data = { name: "Hacked Name" }

    put "/api/v1/clothing_items/#{other_item.id}", params: update_data, headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "DELETE /api/v1/clothing_items/:id deletes clothing item" do
    item = create(:clothing_item, user: @user)

    delete "/api/v1/clothing_items/#{item.id}", headers: api_v1_headers(@token)

    assert_success_response

    # Verify item was deleted
    assert_raises(ActiveRecord::RecordNotFound) { item.reload }
  end

  test "DELETE /api/v1/clothing_items/:id for other user's item returns 404" do
    other_item = create(:clothing_item, user: @other_user)

    delete "/api/v1/clothing_items/#{other_item.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "POST /api/v1/clothing_items/:id/photo uploads photo" do
    item = create(:clothing_item, user: @user)

    # Mock file upload
    photo_data = {
      photo: fixture_file_upload("sample_image.jpg", "image/jpeg")
    }

    post "/api/v1/clothing_items/#{item.id}/photo", params: photo_data, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["item"]["photo_url"].present?, "Should return photo URL"

    # Verify photo was attached
    item.reload
    assert item.photo.attached?, "Photo should be attached"
  end

  test "POST /api/v1/clothing_items/:id/photo with invalid file returns error" do
    item = create(:clothing_item, user: @user)

    # Mock invalid file upload
    photo_data = {
      photo: fixture_file_upload("sample_text.txt", "text/plain")
    }

    post "/api/v1/clothing_items/#{item.id}/photo", params: photo_data, headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["details"]["photo"].present?, "Expected photo validation error"
  end

  private

  def generate_jwt_token(user)
    "jwt_token_for_#{user.id}"
  end
end
