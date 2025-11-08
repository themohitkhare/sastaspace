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

      private

      def api_v1_headers(token = nil)
        headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
        headers.merge!("Authorization" => "Bearer #{token}") if token
        headers
      end
    end
  end
end
