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

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end
end
