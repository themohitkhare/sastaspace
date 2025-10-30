require "test_helper"

class Api::V1::InventoryItemsAttachmentsTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  test "POST /api/v1/inventory_items/:id/primary_image attaches image" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{@item.id}/primary_image", params: { image: file }, headers: api_v1_headers(@token)
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["data"]["image_url"].present?
  end

  test "POST /api/v1/inventory_items/:id/primary_image without image returns 400" do
    post "/api/v1/inventory_items/#{@item.id}/primary_image", headers: api_v1_headers(@token)
    assert_response :bad_request
  end

  test "POST /api/v1/inventory_items/:id/additional_images attaches images" do
    files = [ fixture_file_upload("sample_image.jpg", "image/jpeg") ]
    post "/api/v1/inventory_items/#{@item.id}/additional_images", params: { images: files }, headers: api_v1_headers(@token)
    assert_response :success
    body = JSON.parse(@response.body)
    assert body["data"]["image_urls"].is_a?(Array)
    assert_equal 1, body["data"]["image_urls"].size
  end

  test "POST /api/v1/inventory_items/:id/additional_images without images returns 400" do
    post "/api/v1/inventory_items/#{@item.id}/additional_images", headers: api_v1_headers(@token)
    assert_response :bad_request
  end

  test "DELETE /api/v1/inventory_items/:id/primary_image detaches image" do
    # attach first
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{@item.id}/primary_image", params: { image: file }, headers: api_v1_headers(@token)

    delete "/api/v1/inventory_items/#{@item.id}/primary_image", headers: api_v1_headers(@token)
    assert_response :success
  end

  test "DELETE /api/v1/inventory_items/:id/additional_images/:image_id handles not found" do
    delete "/api/v1/inventory_items/#{@item.id}/additional_images/999999", headers: api_v1_headers(@token)
    assert_response :not_found
  end
end
