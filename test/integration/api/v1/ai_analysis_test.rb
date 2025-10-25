require "test_helper"

class ApiV1AiAnalysisTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @clothing_item = create(:clothing_item, :with_photo, user: @user)
    @other_user = create(:user)
    @other_token = generate_jwt_token(@other_user)
  end

  test "POST /api/v1/clothing_items/:id/analyze triggers analysis" do
    OllamaStubs.setup_image_analysis_stub

    assert_enqueued_with(job: AnalyzeClothingImageJob) do
      post "/api/v1/clothing_items/#{@clothing_item.id}/analyze",
           headers: api_v1_headers(@token)
    end

    assert_success_response
    body = json_response

    assert body["data"]["message"].include?("Analysis started"), "Should confirm analysis started"
    assert body["data"]["job_id"].present?, "Should return job ID"
  end

  test "POST /api/v1/clothing_items/:id/analyze without photo returns error" do
    item_without_photo = create(:clothing_item, user: @user)

    post "/api/v1/clothing_items/#{item_without_photo.id}/analyze",
         headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["message"].include?("No photo attached"), "Should explain missing photo"
  end

  test "POST /api/v1/clothing_items/:id/analyze for other user's item returns 404" do
    other_item = create(:clothing_item, :with_photo, user: @other_user)

    post "/api/v1/clothing_items/#{other_item.id}/analyze",
         headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "POST /api/v1/clothing_items/:id/analyze with force flag re-analyzes" do
    existing_analysis = create(:ai_analysis, clothing_item: @clothing_item)
    OllamaStubs.setup_image_analysis_stub

    assert_enqueued_with(job: AnalyzeClothingImageJob, args: [ @clothing_item.id, { force: true } ]) do
      post "/api/v1/clothing_items/#{@clothing_item.id}/analyze?force=true",
           headers: api_v1_headers(@token)
    end

    assert_success_response
  end

  test "GET /api/v1/clothing_items/:id/analysis returns analysis results" do
    analysis = create(:ai_analysis, clothing_item: @clothing_item)

    get "/api/v1/clothing_items/#{@clothing_item.id}/analysis",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["analysis"].present?, "Should return analysis data"
    assert_equal analysis.id, body["data"]["analysis"]["id"]
    assert body["data"]["analysis"]["response"].present?, "Should include analysis response"
    assert body["data"]["analysis"]["confidence_score"].present?, "Should include confidence score"
  end

  test "GET /api/v1/clothing_items/:id/analysis returns 404 if no analysis" do
    get "/api/v1/clothing_items/#{@clothing_item.id}/analysis",
        headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "GET /api/v1/clothing_items/:id/analysis for other user's item returns 404" do
    other_item = create(:clothing_item, user: @other_user)
    analysis = create(:ai_analysis, clothing_item: other_item)

    get "/api/v1/clothing_items/#{other_item.id}/analysis",
        headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "GET /api/v1/clothing_items/:id/analysis includes metadata" do
    analysis = create(:ai_analysis, clothing_item: @clothing_item)

    get "/api/v1/clothing_items/#{@clothing_item.id}/analysis",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    analysis_data = body["data"]["analysis"]
    assert analysis_data["model_used"].present?, "Should include model used"
    assert analysis_data["processing_time_ms"].present?, "Should include processing time"
    assert analysis_data["created_at"].present?, "Should include creation timestamp"
  end

  test "GET /api/v1/clothing_items/:id/analysis returns multiple analyses" do
    analysis1 = create(:ai_analysis, clothing_item: @clothing_item, analysis_type: "description")
    analysis2 = create(:ai_analysis, clothing_item: @clothing_item, analysis_type: "styling_tips")

    get "/api/v1/clothing_items/#{@clothing_item.id}/analysis",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert body["data"]["analyses"].present?, "Should return analyses array"
    assert_equal 2, body["data"]["analyses"].length, "Should return both analyses"
  end

  test "GET /api/v1/clothing_items/:id/analysis filters by analysis type" do
    description_analysis = create(:ai_analysis, clothing_item: @clothing_item, analysis_type: "description")
    styling_analysis = create(:ai_analysis, clothing_item: @clothing_item, analysis_type: "styling_tips")

    get "/api/v1/clothing_items/#{@clothing_item.id}/analysis?type=description",
        headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["analyses"].length, "Should return only description analysis"
    assert_equal "description", body["data"]["analyses"].first["analysis_type"]
  end

  test "DELETE /api/v1/clothing_items/:id/analysis deletes analysis" do
    analysis = create(:ai_analysis, clothing_item: @clothing_item)

    delete "/api/v1/clothing_items/#{@clothing_item.id}/analysis/#{analysis.id}",
           headers: api_v1_headers(@token)

    assert_success_response

    # Verify analysis was deleted
    assert_raises(ActiveRecord::RecordNotFound) { analysis.reload }
  end

  test "DELETE /api/v1/clothing_items/:id/analysis for other user's item returns 404" do
    other_item = create(:clothing_item, user: @other_user)
    analysis = create(:ai_analysis, clothing_item: other_item)

    delete "/api/v1/clothing_items/#{other_item.id}/analysis",
           headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "GET /api/v1/ai_analyses returns user's analyses" do
    analysis1 = create(:ai_analysis, clothing_item: @clothing_item)
    other_item = create(:clothing_item, user: @other_user)
    other_analysis = create(:ai_analysis, clothing_item: other_item)

    get "/api/v1/ai_analyses", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["analyses"].length, "Should return only user's analyses"
    assert_equal analysis1.id, body["data"]["analyses"].first["id"]
  end

  test "GET /api/v1/ai_analyses with pagination" do
    # Create multiple analyses
    15.times do
      item = create(:clothing_item, :with_photo, user: @user)
      create(:ai_analysis, clothing_item: item)
    end

    get "/api/v1/ai_analyses?page=1&per_page=10", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 10, body["data"]["analyses"].length, "Should return 10 analyses per page"
    assert body["data"]["pagination"].present?, "Should include pagination info"
  end

  test "GET /api/v1/ai_analyses filters by confidence score" do
    high_conf_analysis = create(:ai_analysis, :high_confidence, clothing_item: @clothing_item)
    low_conf_analysis = create(:ai_analysis, :low_confidence, clothing_item: @clothing_item)

    get "/api/v1/ai_analyses?min_confidence=0.8", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal 1, body["data"]["analyses"].length, "Should return only high confidence analysis"
    assert body["data"]["analyses"].first["confidence_score"] >= 0.8
  end

  private

  def generate_jwt_token(user)
    "jwt_token_for_#{user.id}"
  end
end
