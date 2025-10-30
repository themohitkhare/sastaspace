require "test_helper"

class Api::V1::OutfitsPublicIndexTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/outfits without auth returns empty list" do
    get "/api/v1/outfits", headers: { "Content-Type" => "application/json", "Accept" => "application/json" }
    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal [], body["data"]["outfits"]
  end
end
