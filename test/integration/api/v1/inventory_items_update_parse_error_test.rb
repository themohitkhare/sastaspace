require "test_helper"

class Api::V1::InventoryItemsUpdateParseErrorTest < ActionDispatch::IntegrationTest
  include ApiHelpers

  test "PATCH /api/v1/inventory_items/:id with invalid JSON returns PARSE_ERROR" do
    user = create(:user)
    token = generate_jwt_token(user)
    item = create(:inventory_item, :clothing, user: user)

    # Send invalid JSON body
    headers = auth_headers(token).merge("Content-Type" => "application/json")
    patch "/api/v1/inventory_items/#{item.id}",
      params: "{ invalid_json:",
      headers: headers

    assert_response :bad_request
    body = json_response
    assert_equal false, body["success"]
    assert_equal "PARSE_ERROR", body.dig("error", "code")
  end
end


