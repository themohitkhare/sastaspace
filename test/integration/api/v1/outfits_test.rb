require "test_helper"

class ApiV1OutfitsTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @other_user = create(:user)
    @other_token = generate_jwt_token(@other_user)
  end

  test "GET /api/v1/outfits returns user's outfits" do
    outfit1 = create(:outfit, user: @user, name: "Casual Outfit")
    outfit2 = create(:outfit, user: @user, name: "Formal Outfit")
    other_outfit = create(:outfit, user: @other_user, name: "Other Outfit")

    get "/api/v1/outfits", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 2, body["data"]["outfits"].length, "Should return only user's outfits"
    outfit_names = body["data"]["outfits"].map { |outfit| outfit["name"] }
    assert_includes outfit_names, "Casual Outfit"
    assert_includes outfit_names, "Formal Outfit"
    assert_not_includes outfit_names, "Other Outfit"
  end

  test "GET /api/v1/outfits without auth returns 401" do
    get "/api/v1/outfits", headers: api_v1_headers

    assert_unauthorized_response
  end

  test "GET /api/v1/outfits with occasion filter" do
    casual_outfit = create(:outfit, :casual, user: @user)
    formal_outfit = create(:outfit, :formal, user: @user)

    get "/api/v1/outfits?occasion=casual", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["outfits"].length, "Should return only casual outfits"
    assert_equal "casual", body["data"]["outfits"].first["occasion"]
  end

  test "GET /api/v1/outfits with season filter" do
    summer_outfit = create(:outfit, :summer, user: @user)
    winter_outfit = create(:outfit, :winter, user: @user)

    get "/api/v1/outfits?season=summer", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["outfits"].length, "Should return only summer outfits"
    assert_equal "summer", body["data"]["outfits"].first["season"]
  end

  test "GET /api/v1/outfits with favorites filter" do
    favorite_outfit = create(:outfit, :favorite, user: @user)
    regular_outfit = create(:outfit, user: @user)

    get "/api/v1/outfits?favorites=true", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["outfits"].length, "Should return only favorite outfits"
    assert_equal true, body["data"]["outfits"].first["is_favorite"]
  end

  test "GET /api/v1/outfits with pagination" do
    # Create 25 outfits
    25.times { create(:outfit, user: @user) }

    get "/api/v1/outfits?page=1&per_page=10", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 10, body["data"]["outfits"].length, "Should return 10 outfits per page"
    assert body["data"]["pagination"].present?, "Should include pagination info"
    assert_equal 25, body["data"]["pagination"]["total_count"], "Should show total count"
  end

  test "POST /api/v1/outfits creates new outfit" do
    outfit_data = {
      name: "Test Outfit",
      description: "A test outfit",
      occasion: "casual",
      season: "summer",
      weather_condition: "sunny"
    }

    post "/api/v1/outfits", params: outfit_data, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["outfit"]["id"].present?, "Should return outfit ID"
    assert_equal outfit_data[:name], body["data"]["outfit"]["name"]
    assert_equal outfit_data[:occasion], body["data"]["outfit"]["occasion"]

    # Verify outfit was created
    outfit = Outfit.find(body["data"]["outfit"]["id"])
    assert_equal @user, outfit.user, "Should belong to current user"
  end

  test "POST /api/v1/outfits with invalid data returns validation errors" do
    invalid_data = {
      name: "",
      occasion: "invalid_occasion"
    }

    post "/api/v1/outfits", params: invalid_data, headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response

    assert body["error"]["details"].present?, "Expected validation error details"
    assert body["error"]["details"]["name"].present?, "Expected name validation error"
    assert body["error"]["details"]["occasion"].present?, "Expected occasion validation error"
  end

  test "GET /api/v1/outfits/:id returns specific outfit" do
    outfit = create(:outfit, user: @user, name: "Test Outfit")

    get "/api/v1/outfits/#{outfit.id}", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal outfit.id, body["data"]["outfit"]["id"]
    assert_equal "Test Outfit", body["data"]["outfit"]["name"]
  end

  test "GET /api/v1/outfits/:id for other user's outfit returns 404" do
    other_outfit = create(:outfit, user: @other_user)

    get "/api/v1/outfits/#{other_outfit.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "PUT /api/v1/outfits/:id updates outfit" do
    outfit = create(:outfit, user: @user, name: "Original Name")

    update_data = { name: "Updated Name", occasion: "formal" }

    put "/api/v1/outfits/#{outfit.id}", params: update_data, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal "Updated Name", body["data"]["outfit"]["name"]
    assert_equal "formal", body["data"]["outfit"]["occasion"]

    # Verify outfit was updated
    outfit.reload
    assert_equal "Updated Name", outfit.name
    assert_equal "formal", outfit.occasion
  end

  test "PUT /api/v1/outfits/:id for other user's outfit returns 404" do
    other_outfit = create(:outfit, user: @other_user)

    update_data = { name: "Hacked Name" }

    put "/api/v1/outfits/#{other_outfit.id}", params: update_data, headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "DELETE /api/v1/outfits/:id deletes outfit" do
    outfit = create(:outfit, user: @user)

    delete "/api/v1/outfits/#{outfit.id}", headers: api_v1_headers(@token)

    assert_success_response

    # Verify outfit was deleted
    assert_raises(ActiveRecord::RecordNotFound) { outfit.reload }
  end

  test "DELETE /api/v1/outfits/:id for other user's outfit returns 404" do
    other_outfit = create(:outfit, user: @other_user)

    delete "/api/v1/outfits/#{other_outfit.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "POST /api/v1/outfits/:id/clothing_items adds item to outfit" do
    outfit = create(:outfit, user: @user)
    clothing_item = create(:clothing_item, user: @user)

    post "/api/v1/outfits/#{outfit.id}/clothing_items",
         params: { clothing_item_id: clothing_item.id },
         headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["outfit_item"]["id"].present?, "Should return outfit item ID"
    assert_equal clothing_item.id, body["data"]["outfit_item"]["clothing_item_id"]

    # Verify item was added
    assert outfit.has_clothing_item?(clothing_item), "Outfit should have the clothing item"
  end

  test "POST /api/v1/outfits/:id/clothing_items with position" do
    outfit = create(:outfit, user: @user)
    clothing_item = create(:clothing_item, user: @user)

    post "/api/v1/outfits/#{outfit.id}/clothing_items",
         params: { clothing_item_id: clothing_item.id, position: 5 },
         headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 5, body["data"]["outfit_item"]["position"]
  end

  test "POST /api/v1/outfits/:id/clothing_items with other user's item returns 404" do
    outfit = create(:outfit, user: @user)
    other_item = create(:clothing_item, user: @other_user)

    post "/api/v1/outfits/#{outfit.id}/clothing_items",
         params: { clothing_item_id: other_item.id },
         headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "DELETE /api/v1/outfits/:id/clothing_items/:clothing_item_id removes item from outfit" do
    outfit = create(:outfit, user: @user)
    clothing_item = create(:clothing_item, user: @user)
    outfit.add_clothing_item(clothing_item)

    delete "/api/v1/outfits/#{outfit.id}/clothing_items/#{clothing_item.id}",
           headers: api_v1_headers(@token)

    assert_success_response

    # Verify item was removed
    assert_not outfit.has_clothing_item?(clothing_item), "Outfit should not have the clothing item"
  end

  test "POST /api/v1/outfits/:id/duplicate creates copy of outfit" do
    original_outfit = create(:outfit, :with_items, user: @user)

    post "/api/v1/outfits/#{original_outfit.id}/duplicate",
         headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["outfit"]["id"].present?, "Should return new outfit ID"
    assert_equal original_outfit.name + " (Copy)", body["data"]["outfit"]["name"]
    assert_equal original_outfit.occasion, body["data"]["outfit"]["occasion"]

    # Verify outfit was duplicated
    duplicated_outfit = Outfit.find(body["data"]["outfit"]["id"])
    assert_equal @user, duplicated_outfit.user
    assert_equal original_outfit.clothing_items.count, duplicated_outfit.clothing_items.count
  end

  test "POST /api/v1/outfits/:id/duplicate for other user's outfit returns 404" do
    other_outfit = create(:outfit, user: @other_user)

    post "/api/v1/outfits/#{other_outfit.id}/duplicate",
         headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "PUT /api/v1/outfits/:id/toggle_favorite toggles favorite status" do
    outfit = create(:outfit, user: @user, is_favorite: false)

    put "/api/v1/outfits/#{outfit.id}/toggle_favorite",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal true, body["data"]["outfit"]["is_favorite"]

    # Toggle again
    put "/api/v1/outfits/#{outfit.id}/toggle_favorite",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal false, body["data"]["outfit"]["is_favorite"]
  end

  private

  def generate_jwt_token(user)
    "jwt_token_for_#{user.id}"
  end
end
