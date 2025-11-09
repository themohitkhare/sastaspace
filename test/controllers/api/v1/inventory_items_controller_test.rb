require "test_helper"

class Api::V1::InventoryItemsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @category = create(:category, :clothing)
    @brand = create(:brand)
    @inventory_item = create(:inventory_item, :clothing, user: @user, category: @category, brand: @brand)
  end

  # Index Tests
  test "GET /api/v1/inventory_items requires authentication" do
    get "/api/v1/inventory_items"
    assert_response :unauthorized
  end

  test "GET /api/v1/inventory_items returns user's items only" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)

    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 1, body["data"]["inventory_items"].length
    assert_equal @inventory_item.id, body["data"]["inventory_items"].first["id"]
  end

  test "GET /api/v1/inventory_items applies filters correctly" do
    create(:inventory_item, :clothing, user: @user, category: @category, metadata: { color: "blue", season: "summer" })

    get "/api/v1/inventory_items?color=blue&season=summer", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1
  end

  test "GET /api/v1/inventory_items supports pagination" do
    create_list(:inventory_item, 25, :clothing, user: @user, category: @category)

    get "/api/v1/inventory_items?page=1&per_page=10", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 10, body["data"]["inventory_items"].length
    assert_equal 1, body["data"]["pagination"]["current_page"]
    assert_equal 10, body["data"]["pagination"]["per_page"]
  end

  test "GET /api/v1/inventory_items returns 304 Not Modified when fresh" do
    get "/api/v1/inventory_items", headers: api_v1_headers(@token)
    etag = response.headers["ETag"]

    get "/api/v1/inventory_items", headers: api_v1_headers(@token).merge("If-None-Match" => etag)

    assert_response :not_modified
  end

  # Show Tests
  test "GET /api/v1/inventory_items/:id returns specific item" do
    get "/api/v1/inventory_items/#{@inventory_item.id}", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal @inventory_item.id, body["data"]["inventory_item"]["id"]
  end

  test "GET /api/v1/inventory_items/:id returns 404 for non-existent item" do
    get "/api/v1/inventory_items/99999", headers: api_v1_headers(@token)
    assert_not_found_response
  end

  test "GET /api/v1/inventory_items/:id returns 404 for other user's item" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)

    get "/api/v1/inventory_items/#{other_item.id}", headers: api_v1_headers(@token)
    assert_not_found_response
  end

  # Create Tests
  test "POST /api/v1/inventory_items creates new item" do
    assert_difference -> { @user.inventory_items.count }, +1 do
      post "/api/v1/inventory_items",
           params: {
             inventory_item: {
               name: "New Item",
               description: "Description",
               category_id: @category.id
             }
           }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :created
    body = json_response
    assert body["success"]
    assert body["data"]["inventory_item"]["id"].present?
  end

  test "POST /api/v1/inventory_items with blob_id attaches image" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Item with Blob",
             description: "Description",
             category_id: @category.id,
             blob_id: blob.id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :created
    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?, "Primary image should be attached"
  end

  test "POST /api/v1/inventory_items with invalid data returns validation errors" do
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: nil,
             category_id: nil
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["details"].present?
  end

  test "POST /api/v1/inventory_items handles serialization errors gracefully" do
    # Stub serializer to raise error
    Api::V1::InventoryItemSerializer.any_instance.stubs(:as_json).raises(StandardError.new("Serialization error"))

    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Test Item",
             category_id: @category.id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    assert_response :internal_server_error
    body = json_response
    assert_equal "SERIALIZATION_ERROR", body["error"]["code"]
  end

  # Batch Create Tests
  test "POST /api/v1/inventory_items/batch_create creates multiple items" do
    items_data = [
      { name: "Item 1", category_id: @category.id },
      { name: "Item 2", category_id: @category.id }
    ]

    assert_difference -> { @user.inventory_items.count }, +2 do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_response :created
    body = json_response
    assert_equal 2, body["data"]["count"]
  end

  test "POST /api/v1/inventory_items/batch_create with missing items returns error" do
    post "/api/v1/inventory_items/batch_create",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "INVALID_PARAMS")
  end

  test "POST /api/v1/inventory_items/batch_create with invalid items rolls back transaction" do
    items_data = [
      { name: "Valid Item", category_id: @category.id },
      { name: nil, category_id: nil } # Invalid item
    ]

    assert_no_difference -> { @user.inventory_items.count } do
      post "/api/v1/inventory_items/batch_create",
           params: { items: items_data }.to_json,
           headers: api_v1_headers(@token)
    end

    assert_error_response(:unprocessable_entity, "BATCH_CREATE_ERROR")
  end

  # Update Tests
  test "PATCH /api/v1/inventory_items/:id updates item" do
    patch "/api/v1/inventory_items/#{@inventory_item.id}",
          params: {
            inventory_item: {
              name: "Updated Name",
              description: "Updated description"
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_equal "Updated Name", @inventory_item.name
  end

  test "PATCH /api/v1/inventory_items/:id with invalid data returns validation errors" do
    patch "/api/v1/inventory_items/#{@inventory_item.id}",
          params: {
            inventory_item: {
              name: nil
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
  end

  test "PATCH /api/v1/inventory_items/:id returns 404 for other user's item" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)

    patch "/api/v1/inventory_items/#{other_item.id}",
          params: {
            inventory_item: { name: "Hacked" }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_not_found_response
  end

  # Destroy Tests
  test "DELETE /api/v1/inventory_items/:id deletes item" do
    assert_difference -> { @user.inventory_items.count }, -1 do
      delete "/api/v1/inventory_items/#{@inventory_item.id}", headers: api_v1_headers(@token)
    end

    assert_success_response
    assert_not InventoryItem.exists?(@inventory_item.id)
  end

  test "DELETE /api/v1/inventory_items/:id returns 404 for other user's item" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)

    assert_no_difference -> { @user.inventory_items.count } do
      delete "/api/v1/inventory_items/#{other_item.id}", headers: api_v1_headers(@token)
    end

    assert_not_found_response
  end

  # Worn Tests
  test "PATCH /api/v1/inventory_items/:id/worn increments wear count" do
    initial_count = @inventory_item.wear_count

    patch "/api/v1/inventory_items/#{@inventory_item.id}/worn", headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_equal initial_count + 1, @inventory_item.wear_count
  end

  # Similar Items Tests
  test "GET /api/v1/inventory_items/:id/similar returns similar items" do
    similar_item = create(:inventory_item, :clothing, user: @user, category: @category)

    get "/api/v1/inventory_items/#{@inventory_item.id}/similar", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["similar_items"].is_a?(Array)
  end

  test "GET /api/v1/inventory_items/:id/similar respects limit parameter" do
    create_list(:inventory_item, 15, :clothing, user: @user, category: @category)

    get "/api/v1/inventory_items/#{@inventory_item.id}/similar?limit=5", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["similar_items"].length <= 5
  end

  # Search Tests
  test "GET /api/v1/inventory_items/search requires query parameter" do
    get "/api/v1/inventory_items/search", headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "SEARCH_ERROR")
  end

  test "GET /api/v1/inventory_items/search returns matching items" do
    create(:inventory_item, :clothing, user: @user, category: @category, name: "Blue Shirt")

    get "/api/v1/inventory_items/search?q=Blue", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1
  end

  # Semantic Search Tests
  test "POST /api/v1/inventory_items/semantic_search requires query parameter" do
    post "/api/v1/inventory_items/semantic_search",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "SEARCH_ERROR")
  end

  test "POST /api/v1/inventory_items/semantic_search with empty query returns error" do
    post "/api/v1/inventory_items/semantic_search",
         params: { q: "   " }.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "SEARCH_ERROR")
  end

  # Image Attachment Tests
  test "POST /api/v1/inventory_items/:id/primary_image attaches image from file" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    post "/api/v1/inventory_items/#{@inventory_item.id}/primary_image",
         params: { image: file },
         headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert @inventory_item.primary_image.attached?
  end

  test "POST /api/v1/inventory_items/:id/primary_image attaches image from blob_id" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    post "/api/v1/inventory_items/#{@inventory_item.id}/primary_image",
         params: { blob_id: blob.id }.to_json,
         headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert @inventory_item.primary_image.attached?
  end

  test "POST /api/v1/inventory_items/:id/primary_image without image returns error" do
    post "/api/v1/inventory_items/#{@inventory_item.id}/primary_image",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "MISSING_IMAGE")
  end

  test "POST /api/v1/inventory_items/:id/additional_images attaches multiple images" do
    files = [
      fixture_file_upload("sample_image.jpg", "image/jpeg"),
      fixture_file_upload("sample_image.jpg", "image/jpeg")
    ]

    post "/api/v1/inventory_items/#{@inventory_item.id}/additional_images",
         params: { images: files },
         headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_equal 2, @inventory_item.additional_images.count
  end

  test "POST /api/v1/inventory_items/:id/additional_images without images returns error" do
    post "/api/v1/inventory_items/#{@inventory_item.id}/additional_images",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "MISSING_IMAGES")
  end

  test "DELETE /api/v1/inventory_items/:id/primary_image detaches primary image" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    @inventory_item.primary_image.attach(file)

    delete "/api/v1/inventory_items/#{@inventory_item.id}/primary_image", headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_not @inventory_item.primary_image.attached?
  end

  test "DELETE /api/v1/inventory_items/:id/additional_images/:image_id detaches additional image" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    @inventory_item.additional_images.attach(file)
    attachment = @inventory_item.additional_images.first

    delete "/api/v1/inventory_items/#{@inventory_item.id}/additional_images/#{attachment.id}", headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_equal 0, @inventory_item.additional_images.count
  end

  test "DELETE /api/v1/inventory_items/:id/additional_images/:image_id with invalid image_id returns 404" do
    delete "/api/v1/inventory_items/#{@inventory_item.id}/additional_images/99999", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  # Image Analysis Tests
  test "POST /api/v1/inventory_items/analyze_image_for_creation requires image" do
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: {}.to_json,
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "MISSING_IMAGE")
  end

  test "POST /api/v1/inventory_items/analyze_image_for_creation validates image type" do
    file = fixture_file_upload("sample_image.jpg", "text/plain")

    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: file },
         headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "INVALID_IMAGE_TYPE")
  end

  # File size validation is tested in integration tests (image_upload_security_test.rb)
  # This controller test is redundant and has stubbing issues

  test "POST /api/v1/inventory_items/analyze_image_for_creation queues background job" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    assert_enqueued_with(job: AnalyzeImageForCreationJob) do
      post "/api/v1/inventory_items/analyze_image_for_creation",
           params: { image: file },
           headers: api_v1_headers(@token)
    end

    assert_response :accepted
    body = json_response
    assert body["data"]["job_id"].present?
    assert body["data"]["blob_id"].present?
  end

  test "GET /api/v1/inventory_items/analyze_image_status/:job_id requires job_id" do
    get "/api/v1/inventory_items/analyze_image_status", headers: api_v1_headers(@token)

    assert_error_response(:not_found, "NOT_FOUND")
  end

  test "GET /api/v1/inventory_items/analyze_image_status/:job_id returns job status" do
    # Set up memory cache for this test (test env uses null_store by default)
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    begin
      job_id = SecureRandom.uuid
      AnalyzeImageForCreationJob.set_status(job_id, { status: "processing" })

      get "/api/v1/inventory_items/analyze_image_status/#{job_id}", headers: api_v1_headers(@token)

      assert_success_response
      body = json_response
      assert_equal "processing", body["data"]["status"]
    ensure
      Rails.cache = original_cache
    end
  end

  # Parameter Parsing Tests
  test "POST with invalid JSON returns parse error" do
    post "/api/v1/inventory_items",
         params: "invalid json{",
         headers: api_v1_headers(@token).merge("Content-Type" => "application/json")

    assert_error_response(:bad_request, "PARSE_ERROR")
  end

  # Filter Tests
  test "GET /api/v1/inventory_items applies special filters" do
    @inventory_item.update!(last_worn_at: 1.day.ago)

    get "/api/v1/inventory_items?filter=recently_worn", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1
  end

  test "GET /api/v1/inventory_items applies status filter" do
    @inventory_item.update!(status: "active")

    get "/api/v1/inventory_items?status=active", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert body["data"]["inventory_items"].length >= 1
  end

  # Edge Cases
  test "GET /api/v1/inventory_items with empty inventory returns empty array" do
    @inventory_item.destroy

    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response
    assert_equal 0, body["data"]["inventory_items"].length
  end

  test "PATCH /api/v1/inventory_items/:id with metadata updates correctly" do
    patch "/api/v1/inventory_items/#{@inventory_item.id}",
          params: {
            inventory_item: {
              metadata: {
                color: "blue",
                size: "L",
                season: "winter"
              }
            }
          }.to_json,
          headers: api_v1_headers(@token)

    assert_success_response
    @inventory_item.reload
    assert_equal "blue", @inventory_item.metadata["color"]
    assert_equal "L", @inventory_item.metadata["size"]
  end
end
