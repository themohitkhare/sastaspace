require "test_helper"

module Api
  module V1
    class AiAnalysisTest < ActionDispatch::IntegrationTest
      setup do
        @user = FactoryBot.create(:user)
        @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
        @category = FactoryBot.create(:category, :clothing)
        @inventory_item = FactoryBot.create(:inventory_item,
                                            user: @user,
                                            category: @category,
                                            item_type: "clothing")
      end

      test "POST /api/v1/inventory_items/:id/analyze queues analysis job" do
        assert_enqueued_jobs 1, only: AnalyzeClothingImageJob do
          post "/api/v1/inventory_items/#{@inventory_item.id}/analyze",
               headers: { "Authorization" => "Bearer #{@token}" }
        end

        assert_response :ok
        json_response = JSON.parse(response.body)
        assert json_response["success"]
        assert_equal @inventory_item.id, json_response["data"]["inventory_item_id"]
        assert_equal "analysis_queued", json_response["data"]["status"]
      end

      test "POST /api/v1/ai/analyze also queues analysis job" do
        params = { inventory_item_id: @inventory_item.id }

        assert_enqueued_jobs 1, only: AnalyzeClothingImageJob do
          post "/api/v1/ai/analyze",
               params: params,
               headers: { "Authorization" => "Bearer #{@token}" }
        end

        assert_response :ok
      end

      test "GET /api/v1/inventory_items/:id/analysis retrieves analysis" do
        ai = create(:ai_analysis,
          user: @user,
          inventory_item: @inventory_item
        )

        get "/api/v1/inventory_items/#{@inventory_item.id}/analysis", headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :ok
        body = JSON.parse(response.body)
        assert body["success"]
        assert_equal ai.id, body["data"]["analysis"]["id"]
      end

      test "DELETE /api/v1/inventory_items/:id/analysis deletes analysis" do
        create(:ai_analysis,
          user: @user,
          inventory_item: @inventory_item
        )

        delete "/api/v1/inventory_items/#{@inventory_item.id}/analysis", headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :ok
        body = JSON.parse(response.body)
        assert body["success"]
      end

      test "GET /api/v1/ai/analyses returns paginated analyses" do
        analysis1 = create(:ai_analysis, inventory_item: @inventory_item, user: @user)
        analysis2 = create(:ai_analysis, inventory_item: @inventory_item, user: @user)

        get "/api/v1/ai/analyses",
            headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :ok
        json_response = JSON.parse(response.body)
        assert json_response["success"]
        assert_equal 2, json_response["data"]["analyses"].length
        assert_equal 2, json_response["data"]["pagination"]["total_count"]
      end

      test "requires authentication" do
        post "/api/v1/inventory_items/#{@inventory_item.id}/analyze"

        assert_response :unauthorized
      end

      test "cannot access other user's inventory item analysis" do
        other_user = FactoryBot.create(:user)
        other_inventory_item = FactoryBot.create(:inventory_item,
                                                  user: other_user,
                                                  category: @category,
                                                  item_type: "clothing")

        post "/api/v1/inventory_items/#{other_inventory_item.id}/analyze",
             headers: { "Authorization" => "Bearer #{@token}" }

        assert_response :not_found
      end
    end
  end
end
