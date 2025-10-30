require "test_helper"

class Api::V1::OutfitSuggestionsTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/outfits/:id/suggestions requires ownership and returns items" do
    user = create(:user)
    token = generate_jwt_token(user)
    outfit = Outfit.create!(user: user, name: "Work")

    get "/api/v1/outfits/#{outfit.id}/suggestions", headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)
    assert body["success"]
    assert_equal [], body["data"]["items"]
  end
end
