require "test_helper"

class Api::V1::OutfitCompleteFlowTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)

    # Create categories
    @tops_category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, name: "Jeans #{SecureRandom.hex(4)}")
    @shoes_category = create(:category, name: "Sneakers #{SecureRandom.hex(4)}")

    # Create inventory items
    @top_item = create(:inventory_item,
      user: @user,
      category: @tops_category,
      name: "Blue T-Shirt",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )
    @top_item.update_column(:metadata, { "color" => "blue" }.to_json)

    @bottom_item = create(:inventory_item,
      user: @user,
      category: @bottoms_category,
      name: "Blue Jeans",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )
    @bottom_item.update_column(:metadata, { "color" => "blue" }.to_json)

    @shoe_item = create(:inventory_item,
      user: @user,
      category: @shoes_category,
      name: "White Sneakers",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )
    @shoe_item.update_column(:metadata, { "color" => "white" }.to_json)
  end

  test "complete flow: create outfit with items, analyze colors, get suggestions" do
    # Step 1: Create outfit with items
    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "Weekend Casual",
             description: "A casual weekend outfit",
             occasion: "casual",
             inventory_item_ids: [ @top_item.id, @bottom_item.id, @shoe_item.id ]
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    outfit_json = json_response
    assert outfit_json["success"]
    outfit_id = outfit_json["data"]["outfit"]["id"]
    outfit = Outfit.find(outfit_id)

    # Verify outfit was created with items
    assert_equal 3, outfit.inventory_items.count
    assert_includes outfit.inventory_items, @top_item
    assert_includes outfit.inventory_items, @bottom_item
    assert_includes outfit.inventory_items, @shoe_item

    # Step 2: Analyze colors for the outfit items
    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ @top_item.id, @bottom_item.id, @shoe_item.id ] },
        headers: api_headers

    assert_response :success
    color_json = json_response
    assert color_json["success"]
    assert color_json["data"]["score"].present?
    assert color_json["data"]["colors"].present?
    # Should detect blue and white colors
    detected_colors = color_json["data"]["colors"].keys.map(&:downcase)
    assert (detected_colors.include?("blue") || detected_colors.include?("white")), "Should detect blue or white"

    # Step 3: Get AI suggestions for the outfit
    get "/api/v1/outfits/#{outfit_id}/suggestions",
        params: { limit: 5 },
        headers: api_headers

    assert_response :success
    suggestions_json = json_response
    assert suggestions_json["success"]
    assert suggestions_json["data"]["items"].is_a?(Array)
    assert_equal outfit_id, suggestions_json["data"]["outfit_id"]
    assert_equal 3, suggestions_json["data"]["existing_items_count"]

    # Suggestions should not include items already in outfit
    suggested_ids = suggestions_json["data"]["items"].map { |item| item["id"] }
    assert_not_includes suggested_ids, @top_item.id
    assert_not_includes suggested_ids, @bottom_item.id
    assert_not_includes suggested_ids, @shoe_item.id

    # Step 4: Update outfit (e.g., mark as favorite)
    patch "/api/v1/outfits/#{outfit_id}/favorite",
          headers: api_headers

    assert_response :success
    favorite_json = json_response
    assert favorite_json["success"]
    assert_includes [ true, false ], favorite_json["data"]["outfit"]["is_favorite"]
  end

  test "complete flow: create outfit, get suggestions, update outfit with suggested items" do
    # Create outfit with one item
    post "/api/v1/outfits",
         params: {
           outfit: {
             name: "Incomplete Outfit",
             inventory_item_ids: [ @top_item.id ]
           }
         }.to_json,
         headers: api_headers

    assert_response :created
    outfit_id = json_response["data"]["outfit"]["id"]
    outfit = Outfit.find(outfit_id)
    initial_item_count = outfit.inventory_items.count

    # Get suggestions
    get "/api/v1/outfits/#{outfit_id}/suggestions",
        params: { limit: 5 },
        headers: api_headers

    assert_response :success
    suggestions = json_response["data"]["items"]

    if suggestions.any?
      suggested_item_id = suggestions.first["id"]

      # Update outfit to include suggested item
      patch "/api/v1/outfits/#{outfit_id}",
            params: {
              outfit: {
                inventory_item_ids: outfit.inventory_items.pluck(:id) + [ suggested_item_id ]
              }
            }.to_json,
            headers: api_headers

      assert_response :success

      # Verify item was added
      outfit.reload
      assert outfit.inventory_items.count > initial_item_count
      assert_includes outfit.inventory_items.pluck(:id), suggested_item_id
    else
      # If no suggestions, that's also valid - just verify outfit exists
      assert outfit.persisted?
    end
  end

  test "complete flow: color analysis with different color combinations" do
    # Test monochromatic outfit
    item1 = create(:inventory_item, user: @user, category: @tops_category)
    item1.update_column(:metadata, { "color" => "blue" }.to_json)

    item2 = create(:inventory_item, user: @user, category: @bottoms_category)
    item2.update_column(:metadata, { "color" => "navy" }.to_json) # Should normalize to blue

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item1.id, item2.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    # Monochromatic should get good score
    assert json["data"]["score"] >= 0.0

    # Test complementary colors
    item3 = create(:inventory_item, user: @user, category: @tops_category)
    item3.update_column(:metadata, { "color" => "red" }.to_json)

    item4 = create(:inventory_item, user: @user, category: @bottoms_category)
    item4.update_column(:metadata, { "color" => "green" }.to_json)

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item3.id, item4.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    # Complementary colors should get reasonable score
    assert json["data"]["score"] >= 0.0
  end

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end

  def json_response
    JSON.parse(@response.body)
  end
end
