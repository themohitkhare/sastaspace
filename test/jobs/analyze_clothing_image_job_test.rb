require "test_helper"

class AnalyzeClothingImageJobTest < ActiveJob::TestCase
  def setup
    @clothing_item = create(:clothing_item, :with_photo)
  end

  test "job enqueues successfully" do
    assert_enqueued_with(job: AnalyzeClothingImageJob) do
      AnalyzeClothingImageJob.perform_later(@clothing_item.id)
    end
  end

  test "job performs analysis and saves result" do
    OllamaStubs.setup_image_analysis_stub

    assert_difference "AiAnalysis.count", 1 do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id)
    end

    analysis = AiAnalysis.last
    assert_equal @clothing_item, analysis.clothing_item
    assert analysis.response.present?, "Should save analysis response"
    assert analysis.model_used.present?, "Should save model used"
    assert analysis.processing_time_ms > 0, "Should track processing time"
  end

  test "job handles analysis failure gracefully" do
    OllamaStubs.setup_image_analysis_error_stub

    assert_no_difference "AiAnalysis.count" do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id)
    end

    # Should not raise exception
  end

  test "job handles missing clothing item" do
    OllamaStubs.setup_image_analysis_stub

    assert_no_difference "AiAnalysis.count" do
      AnalyzeClothingImageJob.perform_now(99999)
    end

    # Should not raise exception
  end

  test "job handles item without photo" do
    item_without_photo = create(:clothing_item)

    assert_no_difference "AiAnalysis.count" do
      AnalyzeClothingImageJob.perform_now(item_without_photo.id)
    end
  end

  test "job skips analysis if already exists and not forced" do
    existing_analysis = create(:ai_analysis, clothing_item: @clothing_item)

    assert_no_difference "AiAnalysis.count" do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id)
    end
  end

  test "job performs analysis if forced" do
    existing_analysis = create(:ai_analysis, clothing_item: @clothing_item)
    OllamaStubs.setup_image_analysis_stub

    assert_difference "AiAnalysis.count", 1 do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id, force: true)
    end
  end

  test "job updates clothing item with analysis metadata" do
    OllamaStubs.setup_image_analysis_stub

    AnalyzeClothingImageJob.perform_now(@clothing_item.id)

    @clothing_item.reload
    assert @clothing_item.last_analyzed_at.present?, "Should update last analyzed timestamp"
    assert @clothing_item.analysis_status == "completed", "Should update analysis status"
  end

  test "job sets analysis status to failed on error" do
    OllamaStubs.setup_image_analysis_error_stub

    AnalyzeClothingImageJob.perform_now(@clothing_item.id)

    @clothing_item.reload
    assert @clothing_item.analysis_status == "failed", "Should set failed status"
  end

  test "job processes multiple items in batch" do
    items = create_list(:clothing_item, 3, :with_photo)
    OllamaStubs.setup_image_analysis_stub

    assert_difference "AiAnalysis.count", 3 do
      items.each do |item|
        AnalyzeClothingImageJob.perform_now(item.id)
      end
    end
  end

  test "job respects rate limiting" do
    # Mock rate limit exceeded
    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_return(
        status: 429,
        headers: { "Content-Type" => "application/json" },
        body: { "error" => "Rate limit exceeded" }.to_json
      )

    assert_no_difference "AiAnalysis.count" do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id)
    end

    @clothing_item.reload
    assert @clothing_item.analysis_status == "rate_limited", "Should set rate limited status"
  end

  test "job retries on transient errors" do
    # Mock transient error followed by success
    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_return(
        { status: 500, body: "Internal Server Error" },
        { status: 200, body: { "response" => "Analysis result" }.to_json }
      )

    assert_difference "AiAnalysis.count", 1 do
      AnalyzeClothingImageJob.perform_now(@clothing_item.id)
    end
  end
end
