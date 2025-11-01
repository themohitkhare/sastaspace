require "test_helper"

class Api::V1::InventoryItemsBatchCreateTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @category1 = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}")
    @category2 = create(:category, name: "Jeans #{SecureRandom.hex(4)}")
    @brand = create(:brand, name: "Nike #{SecureRandom.hex(4)}")
    @image_file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    @blob = ActiveStorage::Blob.create_and_upload!(
      io: @image_file.open,
      filename: @image_file.original_filename,
      content_type: @image_file.content_type
    )
  end

  test "POST /api/v1/inventory_items/batch_create creates multiple items" do
    items_data = [
      {
        name: "Blue T-Shirt",
        description: "A blue cotton t-shirt",
        category_id: @category1.id,
        blob_id: @blob.id
      },
      {
        name: "Blue Jeans",
        description: "Blue denim jeans",
        category_id: @category2.id,
        blob_id: @blob.id
      }
    ]

    assert_difference -> { @user.inventory_items.count }, 2 do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :created
    body = json_response
    assert body["success"]
    assert_equal 2, body["data"]["count"]
    assert_equal 2, body["data"]["inventory_items"].length

    # Verify items were created correctly
    item1 = InventoryItem.find_by(name: "Blue T-Shirt")
    item2 = InventoryItem.find_by(name: "Blue Jeans")

    assert_not_nil item1, "Item1 should exist"
    assert_not_nil item2, "Item2 should exist"
    # Reload to get latest data
    item1.reload
    item2.reload

    # Check that categories match - reload the categories to ensure they exist
    @category1.reload
    @category2.reload

    # Verify the categories exist in the database
    assert Category.exists?(@category1.id), "Category1 should exist with id #{@category1.id}"
    assert Category.exists?(@category2.id), "Category2 should exist with id #{@category2.id}"

    assert_equal @category1.id, item1.category_id, "Item1 category_id should be #{@category1.id} (#{@category1.name}), got #{item1.category_id} (#{item1.category&.name})"
    assert_equal @category2.id, item2.category_id, "Item2 category_id should be #{@category2.id} (#{@category2.name}), got #{item2.category_id} (#{item2.category&.name})"
    assert item1.primary_image.attached?, "First item should have image attached"
    assert item2.primary_image.attached?, "Second item should have image attached"
  end

  test "POST /api/v1/inventory_items/batch_create requires authentication" do
    post "/api/v1/inventory_items/batch_create",
         params: { items: [] }.to_json,
         headers: { "Content-Type" => "application/json" }

    assert_response :unauthorized
  end

  test "POST /api/v1/inventory_items/batch_create rejects missing items array" do
    post "/api/v1/inventory_items/batch_create",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_equal false, body["success"]
    assert_equal "INVALID_PARAMS", body["error"]["code"]
  end

  test "POST /api/v1/inventory_items/batch_create rejects empty items array" do
    post "/api/v1/inventory_items/batch_create",
         params: { items: [] }.to_json,
         headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_equal false, body["success"]
    assert_equal "INVALID_PARAMS", body["error"]["code"]
  end

  test "POST /api/v1/inventory_items/batch_create handles invalid items gracefully" do
    items_data = [
      {
        name: "Valid Item",
        description: "A valid item",
        category_id: @category1.id
      },
      {
        name: "", # Invalid - name is required
        description: "Invalid item",
        category_id: @category1.id
      }
    ]

    assert_no_difference -> { @user.inventory_items.count } do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :unprocessable_entity
    body = json_response
    assert_equal false, body["success"]
    assert_equal "BATCH_CREATE_ERROR", body["error"]["code"]
    assert body["error"]["details"].is_a?(Array)
  end

  test "POST /api/v1/inventory_items/batch_create handles category normalization" do
    # Create a subcategory
    parent_category = create(:category, name: "Clothing #{SecureRandom.hex(4)}")
    subcategory = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}", parent_id: parent_category.id)

    items_data = [
      {
        name: "Test T-Shirt",
        description: "A t-shirt",
        category_id: subcategory.id
      }
    ]

    post "/api/v1/inventory_items/batch_create",
         params: { items: items_data }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    item = InventoryItem.find_by(name: "Test T-Shirt")
    assert_not_nil item
    assert_equal parent_category.id, item.category_id
    assert_equal subcategory.id, item.subcategory_id
  end

  test "POST /api/v1/inventory_items/batch_create handles items without blob_id" do
    items_data = [
      {
        name: "Item Without Image",
        description: "An item without an image",
        category_id: @category1.id
      }
    ]

    assert_difference -> { @user.inventory_items.count }, 1 do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :created
    item = InventoryItem.find_by(name: "Item Without Image")
    assert_not_nil item
    assert_not item.primary_image.attached?, "Item should not have image when blob_id not provided"
  end

  test "POST /api/v1/inventory_items/batch_create handles items with brand" do
    items_data = [
      {
        name: "Nike T-Shirt",
        description: "A Nike t-shirt",
        category_id: @category1.id,
        brand_id: @brand.id
      }
    ]

    post "/api/v1/inventory_items/batch_create",
         params: { items: items_data }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    item = InventoryItem.find_by(name: "Nike T-Shirt")
    assert_not_nil item
    assert_equal @brand.id, item.brand_id
  end

  test "POST /api/v1/inventory_items/batch_create only creates items for current user" do
    other_user = create(:user)
    items_data = [
      {
        name: "My Item",
        description: "An item",
        category_id: @category1.id
      }
    ]

    post "/api/v1/inventory_items/batch_create",
         params: { items: items_data }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    item = InventoryItem.find_by(name: "My Item")
    assert_equal @user.id, item.user_id
    assert_not_equal other_user.id, item.user_id
  end

  test "POST /api/v1/inventory_items/batch_create is atomic - rolls back on error" do
    items_data = [
      {
        name: "First Item",
        description: "First item",
        category_id: @category1.id
      },
      {
        name: "", # Invalid - will cause rollback
        description: "Invalid item",
        category_id: @category1.id
      },
      {
        name: "Third Item",
        description: "Third item",
        category_id: @category1.id
      }
    ]

    # No items should be created due to transaction rollback
    assert_no_difference -> { @user.inventory_items.count } do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :unprocessable_entity
  end

  private

  def api_v1_headers(token)
    { "Content-Type" => "application/json", "Accept" => "application/json", "Authorization" => "Bearer #{token}" }
  end

  def json_response
    JSON.parse(@response.body)
  end
end
