require "test_helper"

class Api::V1::InventoryItemsAdditionalFiltersTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/inventory_items supports brand and status filters" do
    user = create(:user)
    token = generate_jwt_token(user)
    brand_a = create(:brand, name: "BrandA")
    brand_b = create(:brand, name: "BrandB")
    category = create(:category, :clothing)

    i1 = create(:inventory_item, :clothing, user: user, category: category, brand: brand_a)
    i2 = create(:inventory_item, :clothing, user: user, category: category, brand: brand_b)
    i3 = create(:inventory_item, :clothing, user: user, category: category, brand: brand_a)
    i3.update!(status: :archived)

    get "/api/v1/inventory_items", params: { brand: "BrandA", status: "active" }, headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)
    ids = body["data"]["inventory_items"].map { |it| it["id"] }
    assert_includes ids, i1.id
    assert_not_includes ids, i2.id
    assert_not_includes ids, i3.id
  end
end
