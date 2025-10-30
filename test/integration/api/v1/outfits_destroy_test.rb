require "test_helper"

class Api::V1::OutfitsDestroyTest < ActionDispatch::IntegrationTest
  test "DELETE /api/v1/outfits/:id deletes outfit" do
    user = create(:user)
    token = generate_jwt_token(user)
    outfit = Outfit.create!(user: user, name: "Temp")

    delete "/api/v1/outfits/#{outfit.id}", headers: api_v1_headers(token)

    assert_response :success
    assert_nil Outfit.find_by(id: outfit.id)
  end
end
