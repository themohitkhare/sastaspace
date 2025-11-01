require "test_helper"

class Api::V1::InventoryItemsBlobIdAttachmentTest < ActionDispatch::IntegrationTest
  def setup
    # Use memory store for cache in these tests (test environment uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    # Use a name that definitely matches the clothing pattern
    @category = create(:category, :clothing, name: "T-Shirts #{SecureRandom.hex(4)}")
    @image_file = fixture_file_upload("sample_image.jpg", "image/jpeg")
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  # Test blob_id attachment functionality
  test "POST /api/v1/inventory_items attaches primary image via blob_id" do
    # First, create a blob by uploading an image
    blob = ActiveStorage::Blob.create_and_upload!(
      io: @image_file.open,
      filename: @image_file.original_filename,
      content_type: @image_file.content_type
    )

    # Create inventory item with blob_id
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Test Item with Blob",
             description: "Description",
             category_id: @category.id,
             blob_id: blob.id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    # Accept 201 created or handle 500 error with better error message
    if response.status == 500
      # Try to extract error from HTML response
      error_match = response.body.match(/<pre class="exception_message">(.*?)<\/pre>/m)
      error_msg = error_match ? error_match[1] : response.body[0..1000]
      flunk "Expected 201 but got 500. Error: #{error_msg}"
    end

    assert_response :created
    body = json_response
    assert body["success"], "Response should be successful"

    item_id = body["data"]["inventory_item"]["id"]
    assert item_id.present?, "Item ID should be present"

    item = InventoryItem.find(item_id)

    # Verify the primary image is attached (blob_id attachment might happen asynchronously)
    # Reload to ensure we have the latest state
    item.reload

    # In some test environments, image attachment might be async, so we check if blob exists
    assert item.primary_image.attached?, "Primary image should be attached"
    assert_equal blob.id, item.primary_image.blob.id, "Should attach the correct blob"
  end

  test "POST /api/v1/inventory_items handles invalid blob_id gracefully" do
    invalid_blob_id = 99999

    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "Test Item",
             description: "Description",
             category_id: @category.id,
             blob_id: invalid_blob_id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    # Should still create the item (blob_id failure is non-fatal)
    assert_response :created
    body = json_response
    assert body["success"]

    item = InventoryItem.find(body["data"]["inventory_item"]["id"])
    # Item should be created but without primary image
    assert_not item.primary_image.attached?, "Primary image should not be attached with invalid blob_id"
  end

  test "POST inventory_items_path (controller) attaches primary image via blob_id" do
    # Create a blob
    blob = ActiveStorage::Blob.create_and_upload!(
      io: @image_file.open,
      filename: @image_file.original_filename,
      content_type: @image_file.content_type
    )

    # Stub authentication for HTML controller
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)

    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Test Item with Blob",
          description: "Description",
          category_id: @category.id,
          blob_id: blob.id
        }
      }

      # Debug: If not redirected, check response and validation errors
      unless response.redirect?
        # Try to extract error details from the response
        error_details = "Status: #{response.status}\n"
        error_details += "Body: #{response.body[0..500]}"

        # Try to get validation errors from assigns (if available in integration tests)
        begin
          item = assigns(:inventory_item) if respond_to?(:assigns)
          if item && item.is_a?(InventoryItem) && item.errors.any?
            error_details += "\nValidation errors: #{item.errors.full_messages.join(', ')}"
          end

          # Check category and item_type
          if item
            error_details += "\nCategory: #{item.category&.name}, item_type: #{item.item_type rescue 'error'}"
          end
        rescue NoMethodError
          # assigns might not be available in integration tests
        end

        flunk "Expected redirect but got #{response.status}.\n#{error_details}"
      end
    end

    assert_redirected_to inventory_items_path, "Should redirect after creation"

    item = @user.inventory_items.order(created_at: :desc).first
    assert_not_nil item, "Item should be created"

    # Reload to ensure we have the latest state
    item.reload

    # Verify the primary image is attached
    assert item.primary_image.attached?, "Primary image should be attached. Item errors: #{item.errors.full_messages}"
    assert_equal blob.id, item.primary_image.blob.id, "Should attach the correct blob"
  end

  test "POST inventory_items_path handles invalid blob_id gracefully" do
    # Stub authentication for HTML controller
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)

    invalid_blob_id = 99999

    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Test Item",
          description: "Description",
          category_id: @category.id,
          blob_id: invalid_blob_id
        }
      }

      # Debug: If not redirected, check response and validation errors
      unless response.redirect?
        # Try to extract error details from the response
        error_details = "Status: #{response.status}\n"
        error_details += "Body: #{response.body[0..500]}"

        # Try to get validation errors from assigns (if available in integration tests)
        begin
          item = assigns(:inventory_item) if respond_to?(:assigns)
          if item && item.is_a?(InventoryItem) && item.errors.any?
            error_details += "\nValidation errors: #{item.errors.full_messages.join(', ')}"
          end

          # Check category and item_type
          if item
            error_details += "\nCategory: #{item.category&.name}, item_type: #{item.item_type rescue 'error'}"
          end
        rescue NoMethodError
          # assigns might not be available in integration tests
        end

        flunk "Expected redirect but got #{response.status}.\n#{error_details}"
      end
    end

    assert_redirected_to inventory_items_path

    item = @user.inventory_items.order(created_at: :desc).first
    # Item should be created but without primary image
    assert_not item.primary_image.attached?, "Primary image should not be attached with invalid blob_id"
  end

  test "end-to-end: analyze_image_for_creation returns blob_id, then create uses it" do
    # This test simulates the full AI flow:
    # 1. Upload image for analysis
    # 2. Get blob_id from response
    # 3. Create item using blob_id

    # Step 1: Upload image for analysis
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file },
         headers: auth_headers(@token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["blob_id"].present?, "Response should include blob_id"

    blob_id = body["data"]["blob_id"]

    # Step 2: Create inventory item with the blob_id
    post "/api/v1/inventory_items",
         params: {
           inventory_item: {
             name: "AI Generated Item",
             description: "Description from AI",
             category_id: @category.id,
             blob_id: blob_id
           }
         }.to_json,
         headers: api_v1_headers(@token)

    # Debug: If 500 error, show the error message
    if response.status == 500
      error_match = response.body.match(/<pre class="exception_message">(.*?)<\/pre>/m)
      error_msg = error_match ? error_match[1] : response.body[0..1000]
      flunk "Expected 201 but got 500. Error: #{error_msg}"
    end

    assert_response :created, "Expected 201 but got #{response.status}. Response: #{response.body[0..500]}"
    body = json_response
    assert body["success"]

    item = InventoryItem.find(body["data"]["inventory_item"]["id"])

    # Verify the primary image is attached
    assert item.primary_image.attached?, "Primary image should be attached from blob_id"
    assert_equal blob_id.to_i, item.primary_image.blob.id, "Should attach the blob from analysis"
  end

  test "POST inventory_items_path uses session blob_id fallback when blob_id not in params" do
    # This tests the session fallback mechanism we added
    # Simulate the full flow: API endpoint sets session, then HTML form submission uses it

    # Step 1: Call the API endpoint that sets session[:pending_blob_id]
    # This simulates what happens when user uploads image via AI creation flow
    Api::V1::InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    Api::V1::InventoryItemsController.any_instance.stubs(:current_user).returns(@user)

    # Make API request - this should set session[:pending_blob_id]
    # In Rails integration tests, cookies (including session cookies) are automatically
    # maintained between requests, so the session should persist
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file },
         headers: auth_headers(@token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    blob_id = body["data"]["blob_id"]
    assert blob_id.present?, "Response should include blob_id"

    # Step 2: Now use HTML controller, which should read from session
    # Stub authentication for HTML controller
    # IMPORTANT: We need to stub session access to simulate the session being set by the API call
    # In a real scenario, the session cookie from the API request would be available
    # Here we simulate that by stubbing the session access
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)

    # Stub session to return the blob_id that was set by the API endpoint
    # This simulates the session cookie being shared between API and HTML requests
    # In integration tests, we can't directly access session between requests,
    # so we stub it to test the controller's session fallback logic
    # Create a mock that behaves like Rails session object
    mock_session_hash = HashWithIndifferentAccess.new("pending_blob_id" => blob_id.to_s)
    # Stub session to return our mock when accessed
    InventoryItemsController.any_instance.stubs(:session).returns(mock_session_hash)

    assert_difference -> { @user.inventory_items.count }, +1 do
      # Submit form WITHOUT blob_id in params (simulating JavaScript failure)
      # The HTML controller should read blob_id from session[:pending_blob_id]
      post inventory_items_path, params: {
        inventory_item: {
          name: "Test Item with Session Blob",
          description: "Description",
          category_id: @category.id
          # blob_id intentionally omitted to test session fallback
        }
      }, headers: { "Accept" => "text/html" }
    end

    assert_redirected_to inventory_items_path, "Should redirect after creation"

    item = @user.inventory_items.order(created_at: :desc).first
    assert_not_nil item, "Item should be created"

    # Reload to ensure we have the latest state
    item.reload

    # Verify the primary image is attached via session fallback
    assert item.primary_image.attached?, "Primary image should be attached via session fallback. Item errors: #{item.errors.full_messages}"
    assert_equal blob_id.to_i, item.primary_image.blob.id, "Should attach the blob from session"
  end
end
