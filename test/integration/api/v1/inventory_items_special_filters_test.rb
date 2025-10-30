require "test_helper"

class Api::V1::InventoryItemsSpecialFiltersTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/inventory_items with filter=most_worn orders by wear_count" do
    user = create(:user)
    token = generate_jwt_token(user)
    category = create(:category, :clothing)
    low = create(:inventory_item, :clothing, user: user, category: category, wear_count: 1)
    high = create(:inventory_item, :clothing, user: user, category: category, wear_count: 5)

    get "/api/v1/inventory_items", params: { filter: "most_worn" }, headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)
    ids = body["data"]["inventory_items"].map { |it| it["id"] }
    assert ids.index(high.id) < ids.index(low.id)
  end
end
