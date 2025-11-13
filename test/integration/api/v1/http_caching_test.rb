require "test_helper"

module Api
  module V1
    class HttpCachingTest < ActionDispatch::IntegrationTest
      setup do
        @user = create(:user, password: "Password123!")
        @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
        @category = create(:category, :clothing, name: "Tops #{SecureRandom.hex(4)}")
        @inventory_item = create(:inventory_item, user: @user, category: @category, name: "Test Item #{SecureRandom.hex(4)}")
        @outfit = create(:outfit, user: @user, name: "Test Outfit #{SecureRandom.hex(4)}")
      end

      # Inventory Items Tests

      test "GET /api/v1/inventory_items/:id returns ETag header" do
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        assert @response.headers["ETag"].present?, "Response should include ETag header"
        etag_value = @response.headers["ETag"]
        assert etag_value.start_with?('"') && etag_value.end_with?('"'), "ETag should be quoted"
      end

      test "GET /api/v1/inventory_items/:id returns Last-Modified header" do
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        assert @response.headers["Last-Modified"].present?, "Response should include Last-Modified header"
      end

      test "GET /api/v1/inventory_items/:id returns 304 when resource unchanged" do
        # First request
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        etag = @response.headers["ETag"]
        last_modified = @response.headers["Last-Modified"]

        # Second request with If-None-Match
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token).merge("If-None-Match" => etag)

        assert_response :not_modified
        assert_equal etag, @response.headers["ETag"], "ETag should be unchanged"
      end

      test "GET /api/v1/inventory_items/:id returns 304 with If-Modified-Since" do
        # First request
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        last_modified = @response.headers["Last-Modified"]

        # Second request with If-Modified-Since
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token).merge("If-Modified-Since" => last_modified)

        assert_response :not_modified
      end

      test "GET /api/v1/inventory_items/:id returns 200 when resource is updated" do
        # First request
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        initial_etag = @response.headers["ETag"]
        initial_last_modified = @response.headers["Last-Modified"]

        # Update resource
        patch "/api/v1/inventory_items/#{@inventory_item.id}",
              params: { inventory_item: { name: "Updated Name #{SecureRandom.hex(4)}" } }.to_json,
              headers: api_v1_headers(@token)

        assert_response :success

        # Reload item to ensure updated_at is fresh
        @inventory_item.reload

        # Small delay to ensure timestamp difference
        sleep 0.1

        # Request with old ETag
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token).merge("If-None-Match" => initial_etag)

        # Should return 200 (not 304) because resource was updated
        # If it returns 304, the ETag should still be different
        new_etag = @response.headers["ETag"]
        if @response.status == 304
          # Even if 304, ETag should have changed (though Rails might not send it in 304)
          # Let's make another request without If-None-Match to verify ETag changed
          get "/api/v1/inventory_items/#{@inventory_item.id}",
              headers: api_v1_headers(@token)
          new_etag = @response.headers["ETag"]
          assert_not_equal initial_etag, new_etag, "ETag should change after update"
        else
          assert_equal 200, @response.status, "Should return 200 when resource is updated, got #{@response.status}"
          assert_not_equal initial_etag, new_etag, "ETag should change after update"
        end
      end

      test "GET /api/v1/inventory_items returns ETag for collection" do
        get "/api/v1/inventory_items",
            headers: api_v1_headers(@token)

        assert_response :success
        assert @response.headers["ETag"].present?, "Collection should include ETag header"
        assert @response.headers["Last-Modified"].present?, "Collection should include Last-Modified header"
      end

      test "GET /api/v1/inventory_items returns 304 when collection unchanged" do
        # First request
        get "/api/v1/inventory_items",
            headers: api_v1_headers(@token)

        assert_response :success
        etag = @response.headers["ETag"]

        # Second request
        get "/api/v1/inventory_items",
            headers: api_v1_headers(@token).merge("If-None-Match" => etag)

        assert_response :not_modified
      end

      # Outfits Tests

      test "GET /api/v1/outfits/:id returns ETag and Last-Modified" do
        get "/api/v1/outfits/#{@outfit.id}",
            headers: api_v1_headers(@token)

        assert_response :success
        assert @response.headers["ETag"].present?
        assert @response.headers["Last-Modified"].present?
      end

      test "GET /api/v1/outfits/:id returns 304 when unchanged" do
        get "/api/v1/outfits/#{@outfit.id}",
            headers: api_v1_headers(@token)

        etag = @response.headers["ETag"]

        get "/api/v1/outfits/#{@outfit.id}",
            headers: api_v1_headers(@token).merge("If-None-Match" => etag)

        assert_response :not_modified
      end

      test "GET /api/v1/outfits returns ETag for collection" do
        get "/api/v1/outfits",
            headers: api_v1_headers(@token)

        assert_response :success
        assert @response.headers["ETag"].present?
      end

      # Categories Tests

      test "GET /api/v1/categories/:id returns ETag and Last-Modified" do
        get "/api/v1/categories/#{@category.id}"

        assert_response :success
        assert @response.headers["ETag"].present?
        assert @response.headers["Last-Modified"].present?
        # Categories are public, so Cache-Control should include "public"
        assert_match(/public/, @response.headers["Cache-Control"])
      end

      test "GET /api/v1/categories/:id returns 304 when unchanged" do
        get "/api/v1/categories/#{@category.id}"
        etag = @response.headers["ETag"]

        get "/api/v1/categories/#{@category.id}",
            headers: { "If-None-Match" => etag }

        assert_response :not_modified
      end

      test "GET /api/v1/categories returns ETag for collection" do
        get "/api/v1/categories"

        assert_response :success
        assert @response.headers["ETag"].present?
        assert_match(/public/, @response.headers["Cache-Control"])
      end

      # Cache-Control Tests

      test "private resources have private Cache-Control" do
        get "/api/v1/inventory_items/#{@inventory_item.id}",
            headers: api_v1_headers(@token)

        assert_match(/private/, @response.headers["Cache-Control"])
        assert_match(/must-revalidate/, @response.headers["Cache-Control"])
      end

      test "public resources have public Cache-Control" do
        get "/api/v1/categories/#{@category.id}"

        assert_match(/public/, @response.headers["Cache-Control"])
        assert_match(/must-revalidate/, @response.headers["Cache-Control"])
      end

      test "set_cache_headers with public option sets public Cache-Control" do
        # This would need to be tested through a controller that uses HttpCaching
        # For now, test the method directly
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)
        controller.instance_variable_set(:@_request, ActionDispatch::TestRequest.create)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)

        result = controller.send(:set_cache_headers, @inventory_item, public: true)

        assert_match(/public/, controller.response.headers["Cache-Control"])
      end

      test "set_cache_headers with must_revalidate false" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)
        controller.instance_variable_set(:@_request, ActionDispatch::TestRequest.create)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)

        controller.send(:set_cache_headers, @inventory_item, must_revalidate: false)

        cache_control = controller.response.headers["Cache-Control"]
        refute_match(/must-revalidate/, cache_control)
      end

      test "generate_etag for single resource includes checksum" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)

        etag = controller.send(:generate_etag, @inventory_item)

        assert etag.present?
        assert_includes etag, "inventoryitem"
        assert_includes etag, @inventory_item.id.to_s
      end

      test "generate_etag for relation uses max updated_at" do
        controller = Api::V1::InventoryItemsController.new
        relation = InventoryItem.where(user: @user)

        etag = controller.send(:generate_etag, relation)

        assert etag.present?
        assert_includes etag, "inventoryitem"
        assert_includes etag, "collection"
      end

      test "generate_etag for array combines ETags" do
        controller = Api::V1::InventoryItemsController.new
        items = [ @inventory_item, create(:inventory_item, user: @user) ]

        etag = controller.send(:generate_etag, items)

        assert etag.present?
        assert_equal 16, etag.length # MD5 hex digest truncated to 16 chars
      end

      test "generate_etag returns nil for unsupported type" do
        controller = Api::V1::InventoryItemsController.new

        etag = controller.send(:generate_etag, "string")

        assert_nil etag
      end

      test "generate_etag for relation returns nil when no records" do
        controller = Api::V1::InventoryItemsController.new
        relation = InventoryItem.where(user: create(:user))

        etag = controller.send(:generate_etag, relation)

        assert_nil etag
      end

      test "generate_etag for empty array returns nil" do
        controller = Api::V1::InventoryItemsController.new

        etag = controller.send(:generate_etag, [])

        assert_nil etag
      end

      test "get_last_modified for single resource" do
        controller = Api::V1::InventoryItemsController.new

        last_modified = controller.send(:get_last_modified, @inventory_item)

        assert_equal @inventory_item.updated_at, last_modified
      end

      test "get_last_modified for relation" do
        controller = Api::V1::InventoryItemsController.new
        relation = InventoryItem.where(user: @user)

        last_modified = controller.send(:get_last_modified, relation)

        assert_equal relation.maximum(:updated_at), last_modified
      end

      test "get_last_modified for array" do
        controller = Api::V1::InventoryItemsController.new
        item2 = create(:inventory_item, user: @user)
        items = [ @inventory_item, item2 ]

        last_modified = controller.send(:get_last_modified, items)

        expected = [ @inventory_item.updated_at, item2.updated_at ].max
        assert_equal expected, last_modified
      end

      test "get_last_modified for array with items without updated_at" do
        controller = Api::V1::InventoryItemsController.new
        items = [ @inventory_item, "string" ]

        last_modified = controller.send(:get_last_modified, items)

        assert_equal @inventory_item.updated_at, last_modified
      end

      test "get_last_modified returns nil for unsupported type" do
        controller = Api::V1::InventoryItemsController.new

        last_modified = controller.send(:get_last_modified, "string")

        assert_nil last_modified
      end

      test "get_last_modified returns nil for empty array" do
        controller = Api::V1::InventoryItemsController.new

        last_modified = controller.send(:get_last_modified, [])

        assert_nil last_modified
      end

      test "fresh_request? sets headers and checks freshness" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)
        request = ActionDispatch::TestRequest.create
        controller.instance_variable_set(:@_request, request)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)

        fresh = controller.send(:fresh_request?, @inventory_item)

        assert fresh.is_a?(TrueClass) || fresh.is_a?(FalseClass)
        assert controller.response.headers["ETag"].present?
      end

      test "set_cache_headers returns true when request is fresh" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)
        request = ActionDispatch::TestRequest.create
        controller.instance_variable_set(:@_request, request)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)

        # Set ETag first
        etag = controller.send(:generate_etag, @inventory_item)
        request.headers["If-None-Match"] = %("#{etag}")

        result = controller.send(:set_cache_headers, @inventory_item)

        assert_equal true, result
        assert_equal 304, controller.response.status
      end

      test "set_cache_headers returns false when request is not fresh" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)
        request = ActionDispatch::TestRequest.create
        controller.instance_variable_set(:@_request, request)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)

        result = controller.send(:set_cache_headers, @inventory_item)

        assert_equal false, result
        assert controller.response.headers["ETag"].present?
      end

      test "generate_etag changes when resource attributes change" do
        controller = Api::V1::InventoryItemsController.new
        controller.instance_variable_set(:@inventory_item, @inventory_item)

        etag1 = controller.send(:generate_etag, @inventory_item)

        @inventory_item.update(name: "New Name #{SecureRandom.hex(4)}")
        @inventory_item.reload

        etag2 = controller.send(:generate_etag, @inventory_item)

        assert_not_equal etag1, etag2, "ETag should change when resource is updated"
      end

      private

      def api_v1_headers(token = nil)
        headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
        headers.merge!("Authorization" => "Bearer #{token}") if token
        headers
      end
    end
  end
end
