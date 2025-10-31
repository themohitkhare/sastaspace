require "test_helper"

class Api::V1::OutfitsAdditionalTests < ActionDispatch::IntegrationTest
  include ApiHelpers

  test "GET /api/v1/outfits/:id returns outfit for owner" do
    user = create(:user)
    token = generate_jwt_token(user)
    outfit = user.outfits.create!(name: "Work Fit")

    get "/api/v1/outfits/#{outfit.id}", headers: auth_headers(token)
    assert_response :success
    json = json_response
    assert json["success"]
    assert_equal outfit.id, json.dig("data", "outfit", "id")
  end

  test "PATCH /api/v1/outfits/:id returns validation errors on failure" do
    user = create(:user)
    token = generate_jwt_token(user)
    outfit = user.outfits.create!(name: "Casual")

    patch "/api/v1/outfits/#{outfit.id}",
          headers: auth_headers(token),
          params: { outfit: { name: "" } }
    assert_response :unprocessable_entity
    json = json_response
    assert_equal false, json["success"]
    assert_equal "VALIDATION_ERROR", json.dig("error", "code")
  end
end
