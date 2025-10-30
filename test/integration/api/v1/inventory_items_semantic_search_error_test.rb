require "test_helper"

class Api::V1::InventoryItemsSemanticSearchErrorTest < ActionDispatch::IntegrationTest
  include ApiHelpers

  test "POST /api/v1/inventory_items/semantic_search without q returns SEARCH_ERROR" do
    user = create(:user)
    token = generate_jwt_token(user)
    post "/api/v1/inventory_items/semantic_search", headers: auth_headers(token), params: { }
    assert_response :bad_request
    body = json_response
    assert_equal false, body["success"]
    assert_equal "SEARCH_ERROR", body.dig("error", "code")
  end
end


