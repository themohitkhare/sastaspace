require "test_helper"

class Api::V1::InventoryItemsAttachmentsNotFoundTest < ActionDispatch::IntegrationTest
  include ApiHelpers

  test "DELETE /api/v1/inventory_items/:id/primary_image returns 404 for missing item" do
    user = create(:user)
    token = generate_jwt_token(user)
    headers = auth_headers(token)

    delete "/api/v1/inventory_items/999999/primary_image", headers: headers
    assert_response :not_found
    body = json_response
    assert_equal false, body["success"]
  end

  test "DELETE /api/v1/inventory_items/:id/additional_images/:image_id returns 404 for missing item" do
    user = create(:user)
    token = generate_jwt_token(user)
    headers = auth_headers(token)

    delete "/api/v1/inventory_items/999999/additional_images/123", headers: headers
    assert_response :not_found
    body = json_response
    assert_equal false, body["success"]
  end
end


