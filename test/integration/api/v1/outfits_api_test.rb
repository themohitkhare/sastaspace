require "test_helper"

class Api::V1::OutfitsApiTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
  end

  test "POST /api/v1/outfits creates outfit" do
    post "/api/v1/outfits", params: { outfit: { name: "Weekend Look", description: "Casual" } }.to_json, headers: api_headers
    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_equal "Weekend Look", body["data"]["outfit"]["name"]
  end

  test "GET /api/v1/outfits returns user's outfits" do
    @user.outfits.create!(name: "Office", description: "Formal")
    get "/api/v1/outfits", headers: api_headers
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    assert body["data"]["outfits"].length >= 1
  end

  test "PATCH /api/v1/outfits/:id updates outfit" do
    outfit = @user.outfits.create!(name: "Edit Me")
    patch "/api/v1/outfits/#{outfit.id}", params: { outfit: { name: "Edited" } }.to_json, headers: api_headers
    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal "Edited", body["data"]["outfit"]["name"]
  end

  test "PATCH /api/v1/outfits/:id/wear tracks wear" do
    outfit = @user.outfits.create!(name: "Track Me")
    patch "/api/v1/outfits/#{outfit.id}/wear", headers: api_headers
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
  end

  test "PATCH /api/v1/outfits/:id/favorite toggles favorite" do
    outfit = @user.outfits.create!(name: "Fav Me")
    patch "/api/v1/outfits/#{outfit.id}/favorite", headers: api_headers
    assert_response :success
    body = JSON.parse(@response.body)
    assert_includes [ true, false ], body["data"]["outfit"]["is_favorite"]
  end

  test "POST /api/v1/outfits/:id/duplicate duplicates outfit" do
    outfit = @user.outfits.create!(name: "Dup")
    post "/api/v1/outfits/#{outfit.id}/duplicate", headers: api_headers
    assert_response :created
    body = JSON.parse(@response.body)
    assert_match /Dup \(Copy\)/, body["data"]["outfit"]["name"]
  end

  test "GET /api/v1/outfits/:id requires ownership" do
    other = create(:user)
    outfit = other.outfits.create!(name: "Other")
    get "/api/v1/outfits/#{outfit.id}", headers: api_headers
    assert_response :not_found
  end

  test "POST /api/v1/outfits creates outfit with inventory_item_ids" do
    # Create some inventory items for the user
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    item1 = create(:inventory_item, user: @user, category: category, name: "Item 1")
    item2 = create(:inventory_item, user: @user, category: category, name: "Item 2")

    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "My Outfit",
             description: "An outfit with items",
             inventory_item_ids: [ item1.id, item2.id ]
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]

    outfit = Outfit.find(body["data"]["outfit"]["id"])
    assert_equal 2, outfit.inventory_items.count
    assert_includes outfit.inventory_items, item1
    assert_includes outfit.inventory_items, item2
  end

  test "POST /api/v1/outfits creates outfit without items when inventory_item_ids not provided" do
    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "Empty Outfit",
             description: "An outfit without items"
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]

    outfit = Outfit.find(body["data"]["outfit"]["id"])
    assert_equal 0, outfit.inventory_items.count
  end

  test "POST /api/v1/outfits ignores inventory_item_ids that don't belong to user" do
    other_user = create(:user)
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    my_item = create(:inventory_item, user: @user, category: category, name: "My Item")
    other_item = create(:inventory_item, user: other_user, category: category, name: "Other Item")

    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "My Outfit",
             inventory_item_ids: [ my_item.id, other_item.id ]
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    body = JSON.parse(@response.body)

    outfit = Outfit.find(body["data"]["outfit"]["id"])
    assert_equal 1, outfit.inventory_items.count
    assert_includes outfit.inventory_items, my_item
    assert_not_includes outfit.inventory_items, other_item
  end

  test "POST /api/v1/outfits serializes outfit with items" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")

    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "Test Outfit",
             inventory_item_ids: [ item.id ]
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]
    assert body["data"]["outfit"]["items"].is_a?(Array)
    assert_equal 1, body["data"]["outfit"]["items"].length
    assert_equal item.id, body["data"]["outfit"]["items"].first["id"]
    assert_equal item.name, body["data"]["outfit"]["items"].first["name"]
  end

  test "GET /api/v1/outfits/:id includes items in serialization" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")
    outfit.outfit_items.create!(inventory_item: item, position: 0)

    get "/api/v1/outfits/#{outfit.id}", headers: api_headers

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    assert body["data"]["outfit"]["items"].is_a?(Array)
    assert_equal 1, body["data"]["outfit"]["items"].length
    assert_equal item.id, body["data"]["outfit"]["items"].first["id"]
  end

  test "GET /api/v1/outfits/:id/completeness returns completeness analysis" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")
    outfit.outfit_items.create!(inventory_item: item, position: 0)

    get "/api/v1/outfits/#{outfit.id}/completeness", headers: api_headers

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    assert body["data"]["score"].present?
    assert body["data"]["complete"].is_a?(TrueClass) || body["data"]["complete"].is_a?(FalseClass)
    assert body["data"]["missing_categories"].is_a?(Array)
  end

  test "PATCH /api/v1/outfits/:id/wear updates outfit_items worn_count" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")
    outfit_item = outfit.outfit_items.create!(inventory_item: item, position: 0, worn_count: 0)

    patch "/api/v1/outfits/#{outfit.id}/wear", headers: api_headers

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    outfit_item.reload
    assert_equal 1, outfit_item.worn_count
    assert outfit_item.last_worn_at.present?
  end

  test "POST /api/v1/outfits/:outfit_id/outfit_items creates outfit item" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")

    post "/api/v1/outfits/#{outfit.id}/outfit_items",
         params: { inventory_item_id: item.id, position: 0 }.to_json,
         headers: api_headers

    assert_response :created
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_equal outfit.id, body["data"]["outfit_item"]["outfit_id"]
    assert_equal item.id, body["data"]["outfit_item"]["inventory_item_id"]
  end

  test "DELETE /api/v1/outfits/:outfit_id/outfit_items/:id removes outfit item" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")
    outfit_item = outfit.outfit_items.create!(inventory_item: item, position: 0)

    delete "/api/v1/outfits/#{outfit.id}/outfit_items/#{outfit_item.id}", headers: api_headers

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_nil OutfitItem.find_by(id: outfit_item.id)
  end

  test "PATCH /api/v1/outfits/:outfit_id/outfit_items/:id/update_styling_notes updates styling notes" do
    category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    outfit = @user.outfits.create!(name: "Test Outfit")
    item = create(:inventory_item, user: @user, category: category, name: "Test Item")
    outfit_item = outfit.outfit_items.create!(inventory_item: item, position: 0)

    patch "/api/v1/outfits/#{outfit.id}/outfit_items/#{outfit_item.id}/update_styling_notes",
          params: { styling_notes: "Great for summer" }.to_json,
          headers: api_headers

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    outfit_item.reload
    assert_equal "Great for summer", outfit_item.styling_notes
  end

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end
end
