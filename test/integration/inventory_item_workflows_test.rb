require "test_helper"

class InventoryItemWorkflowsTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    @brand = create(:brand)
  end

  # Complete CRUD Workflow
  test "complete CRUD workflow: create, read, update, delete" do
    # Create
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Workflow Test Item",
             description: "Testing complete workflow",
             category_id: @category.id,
             brand_id: @brand.id,
             metadata: {
               color: "blue",
               size: "M",
               season: "summer"
             }
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    item_id = body["data"]["inventory_item"]["id"]

    # Read
    get "/api/v1/inventory_items/#{item_id}", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert_equal "Workflow Test Item", body["data"]["inventory_item"]["name"]

    # Update
    patch "/api/v1/inventory_items/#{item_id}",
          params: {
            inventory_item: {
              name: "Updated Workflow Item",
              description: "Updated description"
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal "Updated Workflow Item", body["data"]["inventory_item"]["name"]

    # Delete
    assert_difference -> { @user.inventory_items.count }, -1 do
      delete "/api/v1/inventory_items/#{item_id}", headers: api_v1_headers(@token)
    end

    assert_success_response

    # Verify deleted
    get "/api/v1/inventory_items/#{item_id}", headers: api_v1_headers(@token)
    assert_not_found_response
  end

  # Image Upload and Attachment Workflow
  test "complete image upload workflow: analyze, create with blob, attach additional" do
    # Step 1: Analyze image for creation
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: file },
         headers: api_v1_headers(@token)

    assert_response :accepted
    body = json_response
    blob_id = body["data"]["blob_id"]
    job_id = body["data"]["job_id"]

    # Step 2: Create item with blob_id
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Item with AI Analysis",
             description: "Created from analyzed image",
             category_id: @category.id,
             blob_id: blob_id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    item_id = body["data"]["inventory_item"]["id"]
    item = InventoryItem.find(item_id)

    # Verify primary image attached
    assert item.primary_image.attached?, "Primary image should be attached"

    # Step 3: Attach additional images
    additional_files = [
      fixture_file_upload("sample_image.jpg", "image/jpeg"),
      fixture_file_upload("sample_image.jpg", "image/jpeg")
    ]

    post "/api/v1/inventory_items/#{item_id}/additional_images",
         params: { images: additional_files },
         headers: api_v1_headers(@token)

    assert_success_response
    item.reload
    assert_equal 2, item.additional_images.count, "Should have 2 additional images"
  end

  # Batch Operations Workflow
  test "batch create workflow with multiple items" do
    items_data = [
      {
        name: "Batch Item 1",
        category_id: @category.id,
        metadata: { color: "red", size: "S" }
      },
      {
        name: "Batch Item 2",
        category_id: @category.id,
        metadata: { color: "blue", size: "M" }
      },
      {
        name: "Batch Item 3",
        category_id: @category.id,
        metadata: { color: "green", size: "L" }
      }
    ]

    assert_difference -> { @user.inventory_items.count }, +3 do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :created
    body = json_response
    assert_equal 3, body["data"]["count"]

    # Verify all items created
    created_items = body["data"]["inventory_items"]
    assert_equal 3, created_items.length
    assert_equal "Batch Item 1", created_items[0]["name"]
    assert_equal "Batch Item 2", created_items[1]["name"]
    assert_equal "Batch Item 3", created_items[2]["name"]
  end

  # Search and Filter Workflow
  test "search and filter workflow: create items, search, filter, paginate" do
    # Create items with different attributes
    create(:inventory_item, :clothing, user: @user, category: @category,
           name: "Blue Summer Shirt", metadata: { color: "blue", season: "summer" })
    create(:inventory_item, :clothing, user: @user, category: @category,
           name: "Red Winter Jacket", metadata: { color: "red", season: "winter" })
    create(:inventory_item, :clothing, user: @user, category: @category,
           name: "Green Spring Dress", metadata: { color: "green", season: "spring" })

    # Search by name
    get "/api/v1/inventory_items/search?q=Blue", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].any? { |item| item["name"].include?("Blue") }

    # Filter by color
    get "/api/v1/inventory_items?color=blue", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1

    # Filter by season
    get "/api/v1/inventory_items?season=summer", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1

    # Paginate results
    get "/api/v1/inventory_items?page=1&per_page=2", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert_equal 2, body["data"]["inventory_items"].length
    assert_equal 1, body["data"]["pagination"]["current_page"]
  end

  # Wear Tracking Workflow
  test "wear tracking workflow: create item, mark as worn multiple times" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)

    # Mark as worn first time
    patch "/api/v1/inventory_items/#{item.id}/worn", headers: api_v1_headers(@token)
    assert_success_response
    item.reload
    assert_equal 1, item.wear_count

    # Mark as worn second time
    patch "/api/v1/inventory_items/#{item.id}/worn", headers: api_v1_headers(@token)
    assert_success_response
    item.reload
    assert_equal 2, item.wear_count

    # Filter by recently worn
    get "/api/v1/inventory_items?filter=recently_worn", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].any? { |i| i["id"] == item.id }
  end

  # Similar Items Workflow
  test "similar items workflow: create items, find similar" do
    base_item = create(:inventory_item, :clothing, user: @user, category: @category,
                       name: "Base Item", metadata: { color: "blue", size: "M" })
    similar_item = create(:inventory_item, :clothing, user: @user, category: @category,
                          name: "Similar Item", metadata: { color: "blue", size: "L" })

    get "/api/v1/inventory_items/#{base_item.id}/similar", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["similar_items"].is_a?(Array)
    assert body["data"]["base_item"]["id"] == base_item.id
  end

  # Metadata Update Workflow
  test "metadata update workflow: create, update metadata multiple times" do
    item = create(:inventory_item, :clothing, user: @user, category: @category,
                  metadata: { color: "red", size: "S" })

    # First metadata update
    patch "/api/v1/inventory_items/#{item.id}",
          params: {
            inventory_item: {
              metadata: {
                color: "blue",
                size: "M",
                season: "summer"
              }
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response
    item.reload
    assert_equal "blue", item.metadata["color"]
    assert_equal "M", item.metadata["size"]
    assert_equal "summer", item.metadata["season"]

    # Second metadata update (partial)
    patch "/api/v1/inventory_items/#{item.id}",
          params: {
            inventory_item: {
              metadata: {
                color: "green"
              }
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response
    item.reload
    assert_equal "green", item.metadata["color"]
    # Previous values should still exist
    assert_equal "M", item.metadata["size"]
    assert_equal "summer", item.metadata["season"]
  end

  # Image Replacement Workflow
  test "image replacement workflow: attach, detach, reattach" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)

    # Attach primary image
    file1 = fixture_file_upload("sample_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{item.id}/primary_image",
         params: { image: file1 },
         headers: api_v1_headers(@token)

    assert_success_response
    item.reload
    assert item.primary_image.attached?
    first_blob_id = item.primary_image.blob.id

    # Detach primary image
    delete "/api/v1/inventory_items/#{item.id}/primary_image", headers: api_v1_headers(@token)
    assert_success_response
    item.reload
    assert_not item.primary_image.attached?

    # Reattach with new image (different file to ensure different blob ID)
    file2 = fixture_file_upload("test_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{item.id}/primary_image",
         params: { image: file2 },
         headers: api_v1_headers(@token)

    assert_success_response
    item.reload
    assert item.primary_image.attached?
    assert_not_equal first_blob_id, item.primary_image.blob.id, "Reattached image should have different blob ID when using different file"
  end

  # Error Recovery Workflow
  test "error recovery workflow: invalid create, fix, retry" do
    # Attempt invalid create
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: nil, # Invalid
             category_id: nil # Invalid
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")

    # Fix and retry
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Fixed Item",
             description: "Retry after error",
             category_id: @category.id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    assert body["data"]["inventory_item"]["id"].present?
  end

  # Bulk Delete Workflow
  test "bulk operations workflow: create multiple, bulk delete" do
    items = create_list(:inventory_item, 5, :clothing, user: @user, category: @category)

    # Bulk delete via HTML controller
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)

    assert_difference -> { @user.inventory_items.count }, -5 do
      delete bulk_delete_inventory_items_path, params: { item_ids: items.map(&:id) }
    end

    assert_redirected_to inventory_items_path
  end

  # Category Normalization Workflow
  test "category normalization workflow: create with subcategory, verify parent set" do
    parent_category = create(:category, :clothing, name: "Parent #{SecureRandom.hex(4)}")
    subcategory = create(:category, :clothing, parent_id: parent_category.id, name: "Sub #{SecureRandom.hex(4)}")

    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Item with Subcategory",
             category_id: subcategory.id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    item_id = body["data"]["inventory_item"]["id"]
    item = InventoryItem.find(item_id)

    # Category should be normalized to parent
    assert_equal parent_category.id, item.category_id
    assert_equal subcategory.id, item.subcategory_id
  end

  # Complete Lifecycle Workflow
  test "complete item lifecycle: create, update metadata, attach images, mark worn, search, delete" do
    # Create
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Lifecycle Item",
             description: "Testing complete lifecycle",
             category_id: @category.id,
             metadata: {
               color: "blue",
               size: "M"
             }
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    body = json_response
    item_id = body["data"]["inventory_item"]["id"]

    # Update metadata
    patch "/api/v1/inventory_items/#{item_id}",
          params: {
            inventory_item: {
              metadata: {
                season: "summer",
                occasion: "casual"
              }
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response

    # Attach images
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    post "/api/v1/inventory_items/#{item_id}/primary_image",
         params: { image: file },
         headers: api_v1_headers(@token)

    assert_success_response

    # Mark as worn
    patch "/api/v1/inventory_items/#{item_id}/worn", headers: api_v1_headers(@token)
    assert_success_response

    # Search for item
    get "/api/v1/inventory_items/search?q=Lifecycle", headers: api_v1_headers(@token)
    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].any? { |item| item["id"] == item_id }

    # Delete
    delete "/api/v1/inventory_items/#{item_id}", headers: api_v1_headers(@token)
    assert_success_response

    # Verify deleted
    get "/api/v1/inventory_items/#{item_id}", headers: api_v1_headers(@token)
    assert_not_found_response
  end
end
