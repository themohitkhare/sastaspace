require "test_helper"

class Api::V1::InventoryItemsSemanticSearchTest < ActionDispatch::IntegrationTest
  test "POST /api/v1/inventory_items/semantic_search returns items" do
    user = create(:user)
    token = generate_jwt_token(user)
    items = create_list(:inventory_item, 2, :clothing, user: user)

    VectorSearchService.stubs(:semantic_search).returns(items)

    post "/api/v1/inventory_items/semantic_search",
         params: { q: "blue shirt", limit: 5 }.to_json,
         headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal 2, body["data"]["inventory_items"].length
    assert_equal "blue shirt", body["data"]["query"]
  end
end
