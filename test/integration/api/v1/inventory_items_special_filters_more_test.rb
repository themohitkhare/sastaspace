require "test_helper"

class Api::V1::InventoryItemsSpecialFiltersMoreTest < ActionDispatch::IntegrationTest
  include ApiHelpers

  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
  end

  test "GET /api/v1/inventory_items with filter=recently_worn returns only worn items" do
    worn = create(:inventory_item, user: @user, category: @category, last_worn_at: 1.day.ago)
    never = create(:inventory_item, user: @user, category: @category)
    get "/api/v1/inventory_items", params: { filter: "recently_worn" }, headers: auth_headers(@token)
    assert_response :success
    names = json_response.dig("data", "inventory_items").map { |i| i["name"] }
    assert_includes names, worn.name
    refute_includes names, never.name
  end

  test "GET /api/v1/inventory_items with filter=never_worn returns only never worn items" do
    worn = create(:inventory_item, user: @user, category: @category, last_worn_at: 1.day.ago)
    never = create(:inventory_item, user: @user, category: @category)
    get "/api/v1/inventory_items", params: { filter: "never_worn" }, headers: auth_headers(@token)
    assert_response :success
    names = json_response.dig("data", "inventory_items").map { |i| i["name"] }
    assert_includes names, never.name
    refute_includes names, worn.name
  end
end
