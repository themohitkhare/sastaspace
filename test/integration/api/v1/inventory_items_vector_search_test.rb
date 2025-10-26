require "test_helper"

class Api::V1::InventoryItemsVectorSearchTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @auth_token = generate_jwt_token(@user)
    @category = create(:category, name: "tops")
    @brand = create(:brand, name: "Nike")

    @item1 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Blue T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    @item2 = create(:inventory_item,
                   user: @user,
                   category: @category,
                   brand: @brand,
                   name: "Red T-Shirt",
                   item_type: "clothing",
                   embedding_vector: Array.new(1536) { rand(-1.0..1.0) })
  end

  test "GET /api/v1/inventory_items/:id/similar returns similar items" do
    # Mock the vector search
    InventoryItem.stub(:similar_to, [ @item2 ]) do
      get "/api/v1/inventory_items/#{@item1.id}/similar",
          headers: { "Authorization" => "Bearer #{@auth_token}" }

      assert_response :success

      response_data = JSON.parse(response.body)
      assert response_data["success"]
      assert_equal 1, response_data["data"]["similar_items"].count
      assert_equal @item2.id, response_data["data"]["similar_items"].first["id"]
      assert_equal @item1.id, response_data["data"]["base_item"]["id"]
    end
  end

  test "GET /api/v1/inventory_items/:id/similar respects limit parameter" do
    # Mock the vector search
    InventoryItem.stub(:similar_to, [ @item2 ]) do
      get "/api/v1/inventory_items/#{@item1.id}/similar?limit=5",
          headers: { "Authorization" => "Bearer #{@auth_token}" }

      assert_response :success

      response_data = JSON.parse(response.body)
      assert response_data["success"]
      assert_equal 1, response_data["data"]["similar_items"].count
    end
  end

  test "GET /api/v1/inventory_items/:id/similar returns empty array when no vector" do
    @item1.update!(embedding_vector: nil)

    get "/api/v1/inventory_items/#{@item1.id}/similar",
        headers: { "Authorization" => "Bearer #{@auth_token}" }

    assert_response :success

    response_data = JSON.parse(response.body)
    assert response_data["success"]
    assert_equal 0, response_data["data"]["similar_items"].count
  end

  test "POST /api/v1/inventory_items/semantic_search performs semantic search" do
    query = "blue casual shirt"

    # Mock the embedding service and vector search
    Services::EmbeddingService.stub(:generate_text_embedding, Array.new(1536) { rand(-1.0..1.0) }) do
      InventoryItem.stub(:similar_to, [ @item1 ]) do
        post "/api/v1/inventory_items/semantic_search",
             params: { q: query },
             headers: { "Authorization" => "Bearer #{@auth_token}" }

        assert_response :success

        response_data = JSON.parse(response.body)
        assert response_data["success"]
        assert_equal 1, response_data["data"]["inventory_items"].count
        assert_equal query, response_data["data"]["query"]
        assert_equal @item1.id, response_data["data"]["inventory_items"].first["id"]
      end
    end
  end

  test "POST /api/v1/inventory_items/semantic_search requires query parameter" do
    post "/api/v1/inventory_items/semantic_search",
         headers: { "Authorization" => "Bearer #{@auth_token}" }

    assert_response :bad_request

    response_data = JSON.parse(response.body)
    assert_not response_data["success"]
    assert_equal "SEARCH_ERROR", response_data["error"]["code"]
    assert_equal "Search query required", response_data["error"]["message"]
  end

  test "POST /api/v1/inventory_items/semantic_search handles empty query" do
    post "/api/v1/inventory_items/semantic_search",
         params: { q: "" },
         headers: { "Authorization" => "Bearer #{@auth_token}" }

    assert_response :bad_request

    response_data = JSON.parse(response.body)
    assert_not response_data["success"]
    assert_equal "SEARCH_ERROR", response_data["error"]["code"]
  end

  test "POST /api/v1/inventory_items/semantic_search respects limit parameter" do
    query = "blue casual shirt"

    # Mock the embedding service and vector search
    Services::EmbeddingService.stub(:generate_text_embedding, Array.new(1536) { rand(-1.0..1.0) }) do
      InventoryItem.stub(:similar_to, [ @item1, @item2 ]) do
        post "/api/v1/inventory_items/semantic_search",
             params: { q: query, limit: 5 },
             headers: { "Authorization" => "Bearer #{@auth_token}" }

        assert_response :success

        response_data = JSON.parse(response.body)
        assert response_data["success"]
        assert_equal 2, response_data["data"]["inventory_items"].count
      end
    end
  end

  test "POST /api/v1/inventory_items/semantic_search returns empty array when embedding fails" do
    query = "blue casual shirt"

    # Mock embedding generation failure
    Services::EmbeddingService.stub(:generate_text_embedding, nil) do
      post "/api/v1/inventory_items/semantic_search",
           params: { q: query },
           headers: { "Authorization" => "Bearer #{@auth_token}" }

      assert_response :success

      response_data = JSON.parse(response.body)
      assert response_data["success"]
      assert_equal 0, response_data["data"]["inventory_items"].count
    end
  end

  test "vector search endpoints require authentication" do
    get "/api/v1/inventory_items/#{@item1.id}/similar"
    assert_response :unauthorized

    post "/api/v1/inventory_items/semantic_search", params: { q: "test" }
    assert_response :unauthorized
  end

  test "vector search endpoints only return user's items" do
    other_user = create(:user)
    other_item = create(:inventory_item,
                       user: other_user,
                       category: @category,
                       brand: @brand,
                       name: "Other T-Shirt",
                       embedding_vector: Array.new(1536) { rand(-1.0..1.0) })

    # Mock the vector search to return the other user's item
    InventoryItem.stub(:similar_to, [ other_item ]) do
      get "/api/v1/inventory_items/#{@item1.id}/similar",
          headers: { "Authorization" => "Bearer #{@auth_token}" }

      assert_response :success

      response_data = JSON.parse(response.body)
      assert response_data["success"]
      # Should return empty because the similar item belongs to another user
      assert_equal 0, response_data["data"]["similar_items"].count
    end
  end

  private

  def generate_jwt_token(user)
    # This would use your actual JWT generation logic
    # For testing purposes, we'll create a simple token
    JWT.encode({ user_id: user.id, exp: 24.hours.from_now.to_i }, Rails.application.secret_key_base)
  end
end
