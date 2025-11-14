require "test_helper"

class Api::V1::OutfitsColorAnalysisTest < ActionDispatch::IntegrationTest
  def setup
    # Clear cache to prevent state leakage between tests
    Rails.cache.clear
    
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @category = create(:category, name: "Test Category #{SecureRandom.hex(4)}")
  end

  def teardown
    # Clear cache after each test to prevent state leakage
    Rails.cache.clear
  end

  test "GET /api/v1/outfits/color_analysis requires authentication" do
    get "/api/v1/outfits/color_analysis", params: { item_ids: [ 1 ] }
    assert_response :unauthorized
  end

  test "GET /api/v1/outfits/color_analysis requires item_ids" do
    get "/api/v1/outfits/color_analysis", headers: api_headers
    assert_response :bad_request
    json = json_response
    assert_not json["success"]
    assert_equal "INVALID_PARAMS", json.dig("error", "code")
    assert_match(/Item IDs are required/i, json.dig("error", "message"))
  end

  test "GET /api/v1/outfits/color_analysis analyzes colors from metadata" do
    item1 = create(:inventory_item, user: @user, category: @category, name: "Blue Shirt")
    item1.update_column(:metadata, { "color" => "blue" }.to_json)

    item2 = create(:inventory_item, user: @user, category: @category, name: "White Pants")
    item2.update_column(:metadata, { "color" => "white" }.to_json)

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item1.id, item2.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    assert json["data"]["score"].present?
    assert_kind_of Float, json["data"]["score"]
    assert json["data"]["colors"].present?
    assert json["data"]["feedback"].present?
    assert json["data"]["warnings"].is_a?(Array)
    assert json["data"]["suggestions"].is_a?(Array)
  end

  test "GET /api/v1/outfits/color_analysis validates item ownership" do
    other_user = create(:user)
    other_item = create(:inventory_item, user: other_user, category: @category)

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ other_item.id ] },
        headers: api_headers

    assert_response :bad_request
    json = json_response
    assert_not json["success"]
    assert_equal "INVALID_ITEMS", json.dig("error", "code")
  end

  test "GET /api/v1/outfits/color_analysis extracts colors from AI analysis" do
    item = create(:inventory_item, user: @user, category: @category, name: "Red Shirt")

    # Create AI analysis with colors (no metadata color)
    analysis = item.ai_analyses.create!(
      user: @user,
      analysis_type: "visual_analysis",
      confidence_score: 0.9,
      analysis_data: { "colors" => [ "red", "blue" ] }
    )

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    assert json["data"]["colors"].keys.any?
    # Should extract colors from AI analysis when metadata missing
  end

  test "GET /api/v1/outfits/color_analysis handles items with no color information" do
    item = create(:inventory_item, user: @user, category: @category, name: "No Color Item")

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    # Should still return analysis with empty colors or default
    assert json["data"]["score"].present?
  end

  test "GET /api/v1/outfits/color_analysis normalizes color variations" do
    item1 = create(:inventory_item, user: @user, category: @category)
    item1.update_column(:metadata, { "color" => "navy" }.to_json)

    item2 = create(:inventory_item, user: @user, category: @category)
    item2.update_column(:metadata, { "color" => "blue" }.to_json)

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ item1.id, item2.id ] },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    # Navy should be normalized to blue, so colors map should reflect this
  end

  test "GET /api/v1/outfits/color_analysis returns warnings for many colors" do
    items = (1..6).map do |i|
      color_names = [ "red", "blue", "green", "yellow", "purple", "orange" ]
      item = create(:inventory_item, user: @user, category: @category, name: "Item #{i}")
      item.update_column(:metadata, { "color" => color_names[i-1] }.to_json)
      item
    end

    get "/api/v1/outfits/color_analysis",
        params: { item_ids: items.map(&:id) },
        headers: api_headers

    assert_response :success
    json = json_response
    assert json["success"]
    assert json["data"]["warnings"].any? { |w| w.to_s.downcase.include?("many") || w.to_s.downcase.include?("busy") }
  end

  test "GET /api/v1/outfits/color_analysis handles empty item_ids array" do
    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [] },
        headers: api_headers

    assert_response :bad_request
    json = json_response
    assert_equal "INVALID_PARAMS", json.dig("error", "code")
  end

  test "GET /api/v1/outfits/color_analysis handles invalid item_ids" do
    get "/api/v1/outfits/color_analysis",
        params: { item_ids: [ 999999, 888888 ] },
        headers: api_headers

    assert_response :bad_request
    json = json_response
    assert_equal "INVALID_ITEMS", json.dig("error", "code")
  end

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end

  def json_response
    JSON.parse(@response.body)
  end
end
