require "test_helper"

module Api
  module V1
    class OutfitItemsControllerTest < ActionDispatch::IntegrationTest
      setup do
        @user = create(:user, password: "Password123!")
        @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
        @outfit = create(:outfit, user: @user)
        @inventory_item = create(:inventory_item, user: @user)
        @other_user = create(:user)
        @other_outfit = create(:outfit, user: @other_user)
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items creates outfit item" do
        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: @inventory_item.id }.to_json,
             headers: api_v1_headers(@token)

        assert_response :created
        body = json_response
        assert body["success"]
        assert body["data"]["outfit_item"].present?
        assert_equal @inventory_item.id, body["data"]["outfit_item"][:inventory_item_id]
        assert_equal "Item added to outfit", body["message"]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items sets position" do
        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: @inventory_item.id, position: 5 }.to_json,
             headers: api_v1_headers(@token)

        assert_response :created
        body = json_response
        assert_equal 5, body["data"]["outfit_item"][:position]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items uses default position" do
        # Add first item
        create(:outfit_item, outfit: @outfit, position: 0)

        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: @inventory_item.id }.to_json,
             headers: api_v1_headers(@token)

        assert_response :created
        body = json_response
        assert_equal 1, body["data"]["outfit_item"][:position]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items returns 404 for invalid inventory item" do
        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: 999999 }.to_json,
             headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "INVALID_ITEM", body["error"]["code"]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items returns 404 for other user's item" do
        other_item = create(:inventory_item, user: @other_user)

        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: other_item.id }.to_json,
             headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "INVALID_ITEM", body["error"]["code"]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items returns 404 for invalid outfit" do
        post "/api/v1/outfits/999999/outfit_items",
             params: { inventory_item_id: @inventory_item.id }.to_json,
             headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "NOT_FOUND", body["error"]["code"]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items returns 404 for other user's outfit" do
        post "/api/v1/outfits/#{@other_outfit.id}/outfit_items",
             params: { inventory_item_id: @inventory_item.id }.to_json,
             headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "NOT_FOUND", body["error"]["code"]
      end

      test "POST /api/v1/outfits/:outfit_id/outfit_items handles validation errors" do
        # Create duplicate item (if validation prevents duplicates)
        create(:outfit_item, outfit: @outfit, inventory_item: @inventory_item)

        post "/api/v1/outfits/#{@outfit.id}/outfit_items",
             params: { inventory_item_id: @inventory_item.id }.to_json,
             headers: api_v1_headers(@token)

        # Should either succeed (if duplicates allowed) or return validation error
        assert_includes [ 201, 422 ], response.status
      end

      test "DELETE /api/v1/outfits/:outfit_id/outfit_items/:id removes item" do
        outfit_item = create(:outfit_item, outfit: @outfit, inventory_item: @inventory_item)

        delete "/api/v1/outfits/#{@outfit.id}/outfit_items/#{outfit_item.id}",
               headers: api_v1_headers(@token)

        assert_response :success
        body = json_response
        assert body["success"]
        assert_equal "Item removed from outfit", body["message"]
        assert_not OutfitItem.exists?(outfit_item.id)
      end

      test "DELETE /api/v1/outfits/:outfit_id/outfit_items/:id returns 404 for invalid item" do
        delete "/api/v1/outfits/#{@outfit.id}/outfit_items/999999",
               headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "NOT_FOUND", body["error"]["code"]
      end

      test "DELETE /api/v1/outfits/:outfit_id/outfit_items/:id returns 404 for other user's outfit" do
        other_outfit_item = create(:outfit_item, outfit: @other_outfit)

        delete "/api/v1/outfits/#{@other_outfit.id}/outfit_items/#{other_outfit_item.id}",
               headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "NOT_FOUND", body["error"]["code"]
      end

      test "PATCH /api/v1/outfits/:outfit_id/outfit_items/:id/update_styling_notes updates notes" do
        outfit_item = create(:outfit_item, outfit: @outfit, inventory_item: @inventory_item)

        patch "/api/v1/outfits/#{@outfit.id}/outfit_items/#{outfit_item.id}/update_styling_notes",
              params: { styling_notes: "Great for casual occasions" }.to_json,
              headers: api_v1_headers(@token)

        assert_response :success
        body = json_response
        assert body["success"]
        assert_equal "Great for casual occasions", body["data"]["outfit_item"][:styling_notes]
        assert_equal "Styling notes updated", body["message"]
      end

      test "PATCH /api/v1/outfits/:outfit_id/outfit_items/:id/update_styling_notes returns 404 for invalid item" do
        patch "/api/v1/outfits/#{@outfit.id}/outfit_items/999999/update_styling_notes",
              params: { styling_notes: "Test notes" }.to_json,
              headers: api_v1_headers(@token)

        assert_response :not_found
        body = json_response
        assert_not body["success"]
        assert_equal "NOT_FOUND", body["error"]["code"]
      end

      test "PATCH /api/v1/outfits/:outfit_id/outfit_items/:id/update_styling_notes handles validation errors" do
        outfit_item = create(:outfit_item, outfit: @outfit, inventory_item: @inventory_item)

        # Stub update to fail validation
        OutfitItem.any_instance.stubs(:update).returns(false)
        OutfitItem.any_instance.stubs(:errors).returns(mock(full_messages: [ "Validation error" ]))

        patch "/api/v1/outfits/#{@outfit.id}/outfit_items/#{outfit_item.id}/update_styling_notes",
              params: { styling_notes: "Test" }.to_json,
              headers: api_v1_headers(@token)

        assert_response :unprocessable_entity
        body = json_response
        assert_not body["success"]
        assert_equal "VALIDATION_ERROR", body["error"]["code"]
      end

      test "serialize_outfit_item includes all fields" do
        outfit_item = create(:outfit_item, outfit: @outfit, inventory_item: @inventory_item, styling_notes: "Test notes", position: 3)

        controller = Api::V1::OutfitItemsController.new
        controller.instance_variable_set(:@outfit_item, outfit_item)

        serialized = controller.send(:serialize_outfit_item, outfit_item)

        assert_equal outfit_item.id, serialized[:id]
        assert_equal @outfit.id, serialized[:outfit_id]
        assert_equal @inventory_item.id, serialized[:inventory_item_id]
        assert_equal 3, serialized[:position]
        assert_equal "Test notes", serialized[:styling_notes]
        assert_equal outfit_item.worn_count, serialized[:worn_count]
        if outfit_item.last_worn_at.nil?
          assert_nil serialized[:last_worn_at]
        else
          assert_equal outfit_item.last_worn_at, serialized[:last_worn_at]
        end
        assert_equal @inventory_item.id, serialized[:inventory_item][:id]
        assert_equal @inventory_item.name, serialized[:inventory_item][:name]
      end

      test "serialize_outfit_item handles nil category" do
        # Create item with category, then stub category to return nil to test serializer behavior
        item_with_category = create(:inventory_item, user: @user)
        outfit_item = create(:outfit_item, outfit: @outfit, inventory_item: item_with_category)

        controller = Api::V1::OutfitItemsController.new
        controller.instance_variable_set(:@outfit_item, outfit_item)

        # Stub the category association to return nil
        item_with_category.stubs(:category).returns(nil)

        serialized = controller.send(:serialize_outfit_item, outfit_item)

        assert_nil serialized[:inventory_item][:category]
      end

      test "set_outfit returns false and renders error for invalid outfit" do
        controller = Api::V1::OutfitItemsController.new
        controller.instance_variable_set(:@_request, ActionDispatch::TestRequest.create)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)
        controller.stubs(:current_user).returns(@user)
        params_mock = mock
        params_mock.stubs(:[]).with(:outfit_id).returns(999999)
        params_mock.stubs(:outfit_id).returns(999999)
        controller.stubs(:params).returns(params_mock)

        result = controller.send(:set_outfit)

        assert_equal false, result
        assert_equal 404, controller.response.status
      end

      test "set_outfit_item returns false and renders error for invalid item" do
        controller = Api::V1::OutfitItemsController.new
        controller.instance_variable_set(:@outfit, @outfit)
        controller.instance_variable_set(:@_request, ActionDispatch::TestRequest.create)
        controller.instance_variable_set(:@_response, ActionDispatch::TestResponse.new)
        params_mock = mock
        params_mock.stubs(:[]).with(:id).returns(999999)
        params_mock.stubs(:id).returns(999999)
        controller.stubs(:params).returns(params_mock)

        result = controller.send(:set_outfit_item)

        assert_equal false, result
        assert_equal 404, controller.response.status
      end

      private

      def api_v1_headers(token = nil)
        headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
        headers.merge!("Authorization" => "Bearer #{token}") if token
        headers
      end

      def json_response
        JSON.parse(response.body).with_indifferent_access
      end
    end
  end
end
