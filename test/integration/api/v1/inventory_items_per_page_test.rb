require "test_helper"

class Api::V1::InventoryItemsPerPageTest < ActionDispatch::IntegrationTest
  include ApiHelpers

  test "GET /api/v1/inventory_items respects per_page parameter" do
    user = create(:user)
    token = generate_jwt_token(user)
    category = create(:category, :clothing)
    create_list(:inventory_item, 5, :clothing, user: user, category: category)

    get "/api/v1/inventory_items", params: { per_page: 2 }, headers: auth_headers(token)
    assert_response :success
    body = json_response
    assert_equal 2, body.dig("data", "pagination", "per_page")
    assert_equal 2, body.dig("data", "inventory_items").length
  end
end
