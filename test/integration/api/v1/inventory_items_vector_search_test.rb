require "test_helper"

class Api::V1::InventoryItemsVectorSearchTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @auth_token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    @brand = create(:brand)

    @item1 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Blue T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) })

    @item2 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Red T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) })
  end

  test "vector search endpoints require authentication" do
    get "/api/v1/inventory_items/#{@item1.id}/similar"
    assert_response :unauthorized

    post "/api/v1/inventory_items/semantic_search", params: { q: "test" }
    assert_response :unauthorized
  end

  private

  def generate_jwt_token(user)
    Auth::JsonWebToken.encode_access_token(user_id: user.id)
  end
end
