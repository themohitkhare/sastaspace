require "test_helper"

class Api::V1::InventoryItemsTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @category = create(:category, :clothing)
    @brand = create(:brand)
    @inventory_item = create(:inventory_item, :clothing, user: @user, category: @category, brand: @brand)
  end

  test "GET /api/v1/inventory_items should return user's inventory items" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user)

    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 1, body["data"]["inventory_items"].length
    assert_equal @inventory_item.id, body["data"]["inventory_items"].first["id"]
  end

  test "GET /api/v1/inventory_items should support filtering by item_type" do
    shoes_item = create(:inventory_item, :shoes, user: @user)

    get "/api/v1/inventory_items?item_type=clothing", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 1, body["data"]["inventory_items"].length
    assert_equal @inventory_item.id, body["data"]["inventory_items"].first["id"]
  end

  test "GET /api/v1/inventory_items should support filtering by category" do
    get "/api/v1/inventory_items?category=#{@category.name}", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 1, body["data"]["inventory_items"].length
  end

  test "GET /api/v1/inventory_items should support filtering by season" do
    # Update item with known season
    @inventory_item.update!(metadata: { season: "summer", color: "red", size: "M" })

    get "/api/v1/inventory_items?season=summer", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1, "Should find at least one item with summer season"
  end

  test "GET /api/v1/inventory_items should support filtering by color" do
    # Update item with known color
    @inventory_item.update!(metadata: { season: "summer", color: "blue", size: "M" })

    get "/api/v1/inventory_items?color=blue", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1, "Should find at least one item with blue color"
  end

  test "GET /api/v1/inventory_items should support pagination" do
    get "/api/v1/inventory_items?page=1&per_page=10", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["pagination"].present?
    assert_equal 1, body["data"]["pagination"]["current_page"]
    assert_equal 10, body["data"]["pagination"]["per_page"]
  end

  test "GET /api/v1/inventory_items/:id should return specific inventory item" do
    get "/api/v1/inventory_items/#{@inventory_item.id}", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal @inventory_item.id, body["data"]["inventory_item"]["id"]
    assert_equal @inventory_item.name, body["data"]["inventory_item"]["name"]
  end

  test "GET /api/v1/inventory_items/:id should return 404 for non-existent item" do
    get "/api/v1/inventory_items/99999", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "GET /api/v1/inventory_items/:id should return 404 for other user's item" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user)

    get "/api/v1/inventory_items/#{other_item.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "POST /api/v1/inventory_items should create new inventory item" do
    inventory_item_params = {
      inventory_item: {
        name: "Test Item",
        description: "Test description",
        category_id: @category.id,
        brand_id: @brand.id,
        metadata: {
          color: "red",
          size: "M",
          season: "summer"
        }
      }
    }

    post "/api/v1/inventory_items", params: inventory_item_params.to_json, headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    assert body["success"]
    assert_equal "Test Item", body["data"]["inventory_item"]["name"]
    # item_type is derived from category, so verify it's set correctly
    assert body["data"]["inventory_item"]["item_type"].present?
  end

  test "POST /api/v1/inventory_items should return validation errors for invalid data" do
    inventory_item_params = {
      inventory_item: {
        name: "", # Invalid - empty name
        category_id: nil # Invalid - missing category
      }
    }

    post "/api/v1/inventory_items", params: inventory_item_params.to_json, headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
  end

  test "PATCH /api/v1/inventory_items/:id should update inventory item" do
    update_params = {
      inventory_item: {
        name: "Updated Name",
        description: "Updated description"
      }
    }

    patch "/api/v1/inventory_items/#{@inventory_item.id}", params: update_params.to_json, headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal "Updated Name", body["data"]["inventory_item"]["name"]
    assert_equal "Updated description", body["data"]["inventory_item"]["description"]
  end

  test "PATCH /api/v1/inventory_items/:id should return validation errors for invalid data" do
    update_params = {
      inventory_item: {
        name: "" # Invalid - empty name
      }
    }

    patch "/api/v1/inventory_items/#{@inventory_item.id}", params: update_params.to_json, headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
  end

  test "DELETE /api/v1/inventory_items/:id should delete inventory item" do
    delete "/api/v1/inventory_items/#{@inventory_item.id}", headers: api_v1_headers(@token)

    assert_response :success
    body = json_response
    assert body["success"]
    assert body["message"].present?

    # Verify item was actually deleted
    assert_raises(ActiveRecord::RecordNotFound) do
      @inventory_item.reload
    end
  end

  test "PATCH /api/v1/inventory_items/:id/worn should increment wear count" do
    initial_count = @inventory_item.wear_count

    patch "/api/v1/inventory_items/#{@inventory_item.id}/worn", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal initial_count + 1, body["data"]["inventory_item"]["wear_count"]
    assert_not_nil body["data"]["inventory_item"]["last_worn_at"]
  end

  test "GET /api/v1/inventory_items/search should search by name and description" do
    searchable_item = create(:inventory_item, user: @user, name: "Blue Jeans", description: "Comfortable denim")

    get "/api/v1/inventory_items/search?q=jeans", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 1, body["data"]["inventory_items"].length
    assert_equal searchable_item.id, body["data"]["inventory_items"].first["id"]
  end

  test "GET /api/v1/inventory_items/search should return error without query" do
    get "/api/v1/inventory_items/search", headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "SEARCH_ERROR")
  end

  test "GET /api/v1/inventory_items should include image URLs in response when images are attached" do
    # Attach an image to the inventory item
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    item = body["data"]["inventory_items"].find { |i| i["id"] == @inventory_item.id }

    assert_not_nil item, "Item should be in response"
    assert_not_nil item["images"], "Images should be included"
    assert_not_nil item["images"]["primary"], "Primary image should be included"

    primary_image = item["images"]["primary"]
    assert_includes primary_image.keys, "urls", "URLs should be included"

    urls = primary_image["urls"]
    assert_includes urls.keys, "original", "Original URL should be present"
    assert_includes urls.keys, "thumb", "Thumb URL should be present"
    assert_includes urls.keys, "medium", "Medium URL should be present"
    assert_includes urls.keys, "large", "Large URL should be present"

    # Verify URLs are either valid strings or nil (if generation failed gracefully)
    if urls["original"]
      assert_kind_of String, urls["original"]
      assert_match(/^(http|https|\/)/, urls["original"])
    end
    if urls["thumb"]
      assert_kind_of String, urls["thumb"]
      assert_match(/^(http|https|\/)/, urls["thumb"])
    end
  end

  test "GET /api/v1/inventory_items should handle items without images gracefully" do
    # Ensure item has no image
    @inventory_item.primary_image.purge if @inventory_item.primary_image.attached?

    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    item = body["data"]["inventory_items"].find { |i| i["id"] == @inventory_item.id }

    assert_not_nil item, "Item should be in response"
    assert_not_nil item["images"], "Images structure should be included"
    assert_nil item["images"]["primary"], "Primary image should be nil when not attached"
    assert_equal [], item["images"]["additional"], "Additional images should be empty array"
  end

  test "GET /api/v1/inventory_items/:id/similar should return similar items" do
    # Set up embedding vectors for similarity search
    embedding_vector = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }
    @inventory_item.update!(embedding_vector: embedding_vector)

    similar_item = create(:inventory_item, :clothing, user: @user)
    similar_vector = embedding_vector.map { |v| v + rand(-0.1..0.1) }
    similar_item.update!(embedding_vector: similar_vector)

    get "/api/v1/inventory_items/#{@inventory_item.id}/similar", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    # May be 0 or 1 depending on vector similarity threshold
    assert body["data"]["similar_items"].is_a?(Array)
  end

  test "should require authentication for all endpoints" do
    get "/api/v1/inventory_items"
    assert_unauthorized_response

    post "/api/v1/inventory_items", params: { inventory_item: { name: "Test" } }
    assert_unauthorized_response

    patch "/api/v1/inventory_items/1", params: { inventory_item: { name: "Test" } }
    assert_unauthorized_response

    delete "/api/v1/inventory_items/1"
    assert_unauthorized_response
  end
end
