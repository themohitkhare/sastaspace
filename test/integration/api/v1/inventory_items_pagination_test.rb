require "test_helper"

class Api::V1::InventoryItemsPaginationTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    create_list(:inventory_item, 3, :clothing, user: @user, category: @category)
  end

  test "GET /api/v1/inventory_items returns pagination metadata" do
    get "/api/v1/inventory_items", headers: api_v1_headers(@token)
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["data"]["pagination"]["current_page"]
    assert body["data"]["pagination"]["total_pages"]
    assert body["data"]["pagination"]["total_count"]
    assert body["data"]["pagination"]["per_page"]
  end

  test "GET /api/v1/inventory_items/search returns pagination metadata" do
    get "/api/v1/inventory_items/search", params: { q: "Item" }, headers: api_v1_headers(@token)
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["data"]["pagination"]["current_page"]
    assert body["data"]["pagination"]["total_pages"]
    assert body["data"]["pagination"]["total_count"]
    assert body["data"]["pagination"]["per_page"]
  end
end
