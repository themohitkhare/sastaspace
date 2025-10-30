require "test_helper"

class Api::V1::InventoryItemsErrorHandlingTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  test "POST /api/v1/inventory_items parse error returns PARSE_ERROR" do
    malformed_json = "{ invalid_json: }"
    post "/api/v1/inventory_items", params: malformed_json, headers: api_v1_headers(@token)
    assert_response :bad_request
    body = JSON.parse(@response.body)
    assert_equal "PARSE_ERROR", body["error"]["code"]
  end

  test "DELETE /api/v1/inventory_items/:id/additional_images/:image_id removes image" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{@item.id}/additional_images", params: { images: [ file ] }, headers: api_v1_headers(@token)
    assert_response :success
    image_id = @item.reload.additional_images.attachments.first.id

    delete "/api/v1/inventory_items/#{@item.id}/additional_images/#{image_id}", headers: api_v1_headers(@token)
    assert_response :success
  end
end
