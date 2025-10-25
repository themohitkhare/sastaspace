require "test_helper"

class Api::V1::CategoriesTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode(user_id: @user.id)
    
    # Create hierarchical categories
    @clothing = create(:category, name: "Clothing", sort_order: 1)
    @tops = create(:category, name: "Tops", parent_id: @clothing.id, sort_order: 1)
    @t_shirts = create(:category, name: "T-Shirts", parent_id: @tops.id, sort_order: 1)
    @blouses = create(:category, name: "Blouses", parent_id: @tops.id, sort_order: 2)
    
    @shoes = create(:category, name: "Shoes", sort_order: 2)
    @sneakers = create(:category, name: "Sneakers", parent_id: @shoes.id, sort_order: 1)
    
    # Create some inventory items
    @clothing_item = create(:inventory_item, user: @user, category: @t_shirts, item_type: 'clothing')
    # @shoes_item = create(:inventory_item, user: @user, category: @sneakers, item_type: 'shoes')
  end

  test "GET /api/v1/categories should return all categories" do
    get "/api/v1/categories"
    
    assert_success_response
    body = json_response
    assert body["data"]["categories"].length > 0
    
    # Check that categories have required fields
    category = body["data"]["categories"].first
    assert_includes category.keys, "id"
    assert_includes category.keys, "name"
    assert_includes category.keys, "slug"
    assert_includes category.keys, "full_path"
    assert_includes category.keys, "is_root"
    assert_includes category.keys, "is_leaf"
    assert_includes category.keys, "item_count"
  end

  test "GET /api/v1/categories?roots_only=true should return only root categories" do
    get "/api/v1/categories?roots_only=true"
    
    assert_success_response
    body = json_response
    categories = body["data"]["categories"]
    
    # All returned categories should be root categories
    categories.each do |category|
      assert category["is_root"]
    end
    
    # Should include our root categories
    category_names = categories.map { |c| c["name"] }
    assert_includes category_names, "Clothing"
    assert_includes category_names, "Shoes"
  end

  test "GET /api/v1/categories/:id should return specific category" do
    get "/api/v1/categories/#{@clothing.id}"
    
    assert_success_response
    body = json_response
    category = body["data"]["category"]
    
    assert_equal @clothing.id, category["id"]
    assert_equal "Clothing", category["name"]
    assert_equal "clothing", category["slug"]
    assert category["is_root"]
    assert_not category["is_leaf"]
  end

  test "GET /api/v1/categories/tree should return full hierarchical tree" do
    get "/api/v1/categories/tree"
    
    assert_success_response
    body = json_response
    categories = body["data"]["categories"]
    
    # Find clothing category in tree
    clothing_category = categories.find { |c| c["name"] == "Clothing" }
    assert_not_nil clothing_category
    
    # Should have children
    assert clothing_category["children"].length > 0
    
    # Find tops category
    tops_category = clothing_category["children"].find { |c| c["name"] == "Tops" }
    assert_not_nil tops_category
    
    # Should have its own children
    assert tops_category["children"].length > 0
    child_names = tops_category["children"].map { |c| c["name"] }
    assert_includes child_names, "T-Shirts"
    assert_includes child_names, "Blouses"
  end

  test "GET /api/v1/categories/roots should return only root categories" do
    get "/api/v1/categories/roots"
    
    assert_success_response
    body = json_response
    categories = body["data"]["categories"]
    
    # All should be root categories
    categories.each do |category|
      assert category["is_root"]
    end
    
    # Should include our root categories
    category_names = categories.map { |c| c["name"] }
    assert_includes category_names, "Clothing"
    assert_includes category_names, "Shoes"
  end

  test "GET /api/v1/categories/:id/children should return direct children" do
    get "/api/v1/categories/#{@clothing.id}/children"
    
    assert_success_response
    body = json_response
    
    # Should return parent category info
    parent = body["data"]["category"]
    assert_equal @clothing.id, parent["id"]
    
    # Should return children
    children = body["data"]["children"]
    assert children.length > 0
    
    child_names = children.map { |c| c["name"] }
    assert_includes child_names, "Tops"
    
    # Children should not have their own children in this response
    children.each do |child|
      assert_not child.key?("children")
    end
  end

  test "GET /api/v1/categories/:id/inventory_items should require authentication" do
    get "/api/v1/categories/#{@clothing.id}/inventory_items"
    
    assert_response :unauthorized
    body = json_response
    assert_equal "AUTHENTICATION_ERROR", body["error"]["code"]
  end

  test "GET /api/v1/categories/:id/inventory_items should return items in category" do
    get "/api/v1/categories/#{@t_shirts.id}/inventory_items", headers: api_v1_headers(@token)
    
    assert_success_response
    body = json_response
    
    # Should return category info
    category = body["data"]["category"]
    assert_equal @t_shirts.id, category["id"]
    
    # Should return inventory items
    items = body["data"]["inventory_items"]
    assert_equal 1, items.length
    assert_equal @clothing_item.id, items.first["id"]
    
    # Should include pagination
    assert body["data"]["pagination"]
  end

  test "GET /api/v1/categories/:id/inventory_items?include_subcategories=true should include subcategory items" do
    get "/api/v1/categories/#{@tops.id}/inventory_items?include_subcategories=true", headers: api_v1_headers(@token)
    
    assert_success_response
    body = json_response
    
    items = body["data"]["inventory_items"]
    assert_equal 1, items.length
    assert_equal @clothing_item.id, items.first["id"]
    
    # Should indicate subcategories are included
    assert body["data"]["include_subcategories"]
  end

  test "GET /api/v1/categories/:id/inventory_items?include_subcategories=false should not include subcategory items" do
    get "/api/v1/categories/#{@tops.id}/inventory_items?include_subcategories=false", headers: api_v1_headers(@token)
    
    assert_success_response
    body = json_response
    
    items = body["data"]["inventory_items"]
    assert_equal 0, items.length
    
    # Should indicate subcategories are not included
    assert_not body["data"]["include_subcategories"]
  end

  test "GET /api/v1/categories/:id should return 404 for non-existent category" do
    get "/api/v1/categories/99999"
    
    assert_response :not_found
    body = json_response
    assert_equal "NOT_FOUND", body["error"]["code"]
  end

  test "GET /api/v1/categories/:id/children should return 404 for non-existent category" do
    get "/api/v1/categories/99999/children"
    
    assert_response :not_found
    body = json_response
    assert_equal "NOT_FOUND", body["error"]["code"]
  end

  test "GET /api/v1/categories/:id/inventory_items should return 404 for non-existent category" do
    get "/api/v1/categories/99999/inventory_items", headers: api_v1_headers(@token)
    
    assert_response :not_found
    body = json_response
    assert_equal "NOT_FOUND", body["error"]["code"]
  end

  test "category item_count should reflect user's items when authenticated" do
    get "/api/v1/categories/#{@t_shirts.id}", headers: api_v1_headers(@token)
    
    assert_success_response
    body = json_response
    category = body["data"]["category"]
    
    assert_equal 1, category["item_count"]
  end

  test "category item_count should be 0 when not authenticated" do
    get "/api/v1/categories/#{@t_shirts.id}"
    
    assert_success_response
    body = json_response
    category = body["data"]["category"]
    
    assert_equal 0, category["item_count"]
  end

  private

  def api_v1_headers(token)
    {
      "Authorization" => "Bearer #{token}",
      "Content-Type" => "application/json"
    }
  end

  def assert_success_response
    assert_response :success
    body = json_response
    assert body["success"]
    assert body["data"]
    assert body["message"]
    assert body["timestamp"]
  end

  def json_response
    JSON.parse(response.body)
  end
end
