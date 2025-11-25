require "test_helper"

class Api::V1::OutfitsSuggestionsTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)

    # Create categories
    @tops_category = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    @bottoms_category = create(:category, name: "Jeans #{SecureRandom.hex(4)}")
    @shoes_category = create(:category, name: "Sneakers #{SecureRandom.hex(4)}")

    # Create items with vectors for testing
    @top_item = create(:inventory_item,
      user: @user,
      category: @tops_category,
      name: "Blue T-Shirt",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )

    @bottom_item = create(:inventory_item,
      user: @user,
      category: @bottoms_category,
      name: "Blue Jeans",
      embedding_vector: Array.new(1536) { |i| @top_item.embedding_vector[i] + rand(-0.1..0.1) }
    )

    @shoe_item = create(:inventory_item,
      user: @user,
      category: @shoes_category,
      name: "White Sneakers",
      embedding_vector: Array.new(1536) { rand(-1.0..1.0) }
    )

    # Create outfit with one item
    @outfit = @user.outfits.create!(name: "Test Outfit")
    @outfit.outfit_items.create!(inventory_item: @top_item, position: 0)
  end

  test "GET /api/v1/outfits/:id/suggestions returns AI suggestions" do
    get "/api/v1/outfits/#{@outfit.id}/suggestions",
        headers: api_headers

    assert_response :success
    body = json_response
    assert body["success"]
    assert body["data"]["items"].is_a?(Array)
    assert body["data"]["outfit_id"] == @outfit.id
  end

  test "GET /api/v1/outfits/:id/suggestions respects limit parameter" do
    get "/api/v1/outfits/#{@outfit.id}/suggestions?limit=3",
        headers: api_headers

    assert_response :success
    body = json_response
    assert body["success"]
    assert body["data"]["items"].length <= 3
  end

  test "GET /api/v1/outfits/:id/suggestions excludes provided item IDs" do
    get "/api/v1/outfits/#{@outfit.id}/suggestions?exclude_ids[]=#{@bottom_item.id}",
        headers: api_headers

    assert_response :success
    body = json_response
    assert body["success"]

    suggested_ids = body["data"]["items"].map { |item| item["id"] }
    assert_not_includes suggested_ids, @bottom_item.id
    assert_not_includes suggested_ids, @top_item.id # Already in outfit
  end

  test "GET /api/v1/outfits/:id/suggestions requires authentication" do
    get "/api/v1/outfits/#{@outfit.id}/suggestions"

    assert_response :unauthorized
  end

  test "GET /api/v1/outfits/:id/suggestions requires ownership" do
    other_user = create(:user)
    other_outfit = other_user.outfits.create!(name: "Other Outfit")

    get "/api/v1/outfits/#{other_outfit.id}/suggestions",
        headers: api_headers

    assert_response :not_found
  end

  test "GET /api/v1/outfits/:id/suggestions handles outfit with no items" do
    empty_outfit = @user.outfits.create!(name: "Empty Outfit")

    get "/api/v1/outfits/#{empty_outfit.id}/suggestions",
        headers: api_headers

    assert_response :success
    body = json_response
    assert body["success"]
    # May return empty array or suggestions based on user's wardrobe
    assert body["data"]["items"].is_a?(Array)
  end

  test "GET /api/v1/outfits/:id/suggestions returns enhanced suggestion data" do
    get "/api/v1/outfits/#{@outfit.id}/suggestions",
        headers: api_headers

    assert_response :success
    body = json_response
    assert body["success"]

    # Verify enhanced suggestion structure
    if body["data"]["items"].any?
      first_item = body["data"]["items"].first

      # Verify new fields are present
      assert first_item.key?("match_score"), "Should include match_score"
      assert first_item.key?("reasoning"), "Should include reasoning"
      assert first_item.key?("badges"), "Should include badges"

      # Verify reasoning structure
      reasoning = first_item["reasoning"]
      assert reasoning.is_a?(Hash), "Reasoning should be a hash"
      assert reasoning.key?("primary"), "Reasoning should have primary field"
      assert reasoning.key?("details"), "Reasoning should have details field"
      assert reasoning.key?("tags"), "Reasoning should have tags field"
      assert reasoning["tags"].is_a?(Array), "Tags should be an array"

      # Verify match_score is between 0 and 1
      match_score = first_item["match_score"]
      assert match_score.is_a?(Numeric), "match_score should be numeric"
      assert match_score >= 0.0 && match_score <= 1.0, "match_score should be between 0 and 1"

      # Verify badges is an array
      assert first_item["badges"].is_a?(Array), "badges should be an array"
    end
  end

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end

  def json_response
    JSON.parse(@response.body)
  end
end
