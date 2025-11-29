require "test_helper"

class Api::V1::InventoryItemsSimilarLimitTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/inventory_items/:id/similar respects limit param" do
    user = create(:user)
    token = generate_jwt_token(user)
    category = create(:category, :clothing)
    base = create(:inventory_item, :clothing, user: user, category: category)
    # Set vectors
    vec = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand }
    base.update!(embedding_vector: vec)
    # Create two other items with vectors
    i1 = create(:inventory_item, :clothing, user: user, category: category, embedding_vector: vec.map { |v| v + 0.01 })
    i2 = create(:inventory_item, :clothing, user: user, category: category, embedding_vector: vec.map { |v| v - 0.01 })

    get "/api/v1/inventory_items/#{base.id}/similar", params: { limit: 1 }, headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal 1, body["data"]["similar_items"].length
  end
end
