require "test_helper"

class Api::V1::OutfitsCritiqueTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)

    @outfit = create(:outfit, user: @user, name: "Test Outfit", occasion: "casual")

    # Create items for outfit
    @item1 = create(:inventory_item, user: @user, name: "Blue Shirt")
    @item2 = create(:inventory_item, user: @user, name: "Jeans")

    @outfit.outfit_items.create!(inventory_item: @item1, position: 0)
    @outfit.outfit_items.create!(inventory_item: @item2, position: 1)
  end

  test "POST /api/v1/outfits/:id/critique requires authentication" do
    post "/api/v1/outfits/#{@outfit.id}/critique"

    assert_response :unauthorized
  end

  test "POST /api/v1/outfits/:id/critique requires ownership" do
    other_user = create(:user)
    other_outfit = create(:outfit, user: other_user)

    # Stub the service to prevent it from running (since authorize_owner! should catch it first)
    Services::OutfitCritiqueService.expects(:analyze).never

    post "/api/v1/outfits/#{other_outfit.id}/critique",
         headers: api_headers

    # authorize_owner! raises ActiveRecord::RecordNotFound which becomes 404
    assert_response :not_found
  end

  test "POST /api/v1/outfits/:id/critique generates critique" do
    # Stub the critique service using Mocha
    mock_result = {
      "score" => 85,
      "summary" => "Great casual outfit",
      "strengths" => [ "Color coordination", "Style consistency" ],
      "improvements" => [ "Add accessories", "Try different shoes" ],
      "tone" => "Encouraging"
    }

    Services::OutfitCritiqueService.expects(:analyze).returns(mock_result)

    post "/api/v1/outfits/#{@outfit.id}/critique",
         headers: api_headers

    assert_response :success
    body = json_response

    assert body["success"]
    assert_equal 85, body["data"]["score"]
    assert body["data"]["summary"].present?
    assert body["data"]["strengths"].is_a?(Array)
    assert body["data"]["improvements"].is_a?(Array)
  end

  test "POST /api/v1/outfits/:id/critique handles service errors" do
    Services::OutfitCritiqueService.expects(:analyze).returns({ error: "Outfit has no items" })

    post "/api/v1/outfits/#{@outfit.id}/critique",
         headers: api_headers

    assert_response :unprocessable_entity
    body = json_response

    assert_not body["success"]
    assert_equal "CRITIQUE_ERROR", body.dig("error", "code")
  end

  test "POST /api/v1/outfits/:id/critique enforces quota" do
    # Create 3 critiques today (at limit for free user)
    outfit2 = create(:outfit, user: @user)
    3.times do
      AiAnalysis.create!(
        outfit: outfit2,
        user: @user,
        analysis_type: "outfit_critique",
        analysis_data: { score: 80 },
        confidence_score: 0.80,
        created_at: Time.current
      )
    end

    post "/api/v1/outfits/#{@outfit.id}/critique",
         headers: api_headers

    assert_response :forbidden
    body = json_response

    assert_not body["success"]
    assert_equal "QUOTA_EXCEEDED", body.dig("error", "code")
  end

  test "POST /api/v1/outfits/:id/critique allows premium users unlimited critiques" do
    @user.update!(plan_type: "premium")

    # Create many critiques
    10.times do
      AiAnalysis.create!(
        outfit: @outfit,
        user: @user,
        analysis_type: "outfit_critique",
        analysis_data: { "score" => 80 },
        confidence_score: 0.80,
        created_at: Time.current
      )
    end

    mock_result = { "score" => 90, "summary" => "Test" }
    Services::OutfitCritiqueService.expects(:analyze).returns(mock_result)

    post "/api/v1/outfits/#{@outfit.id}/critique",
         headers: api_headers

    assert_response :success
  end

  private

  def api_headers
    { "Authorization" => "Bearer #{@token}", "Content-Type" => "application/json" }
  end

  def json_response
    JSON.parse(@response.body)
  end
end
