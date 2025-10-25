require "test_helper"

class OllamaImageAnalyzerTest < ActiveSupport::TestCase
  def setup
    @service = Ollama::ImageAnalyzer.new
    @inventory_item = create(:inventory_item, :with_photo)
  end

  test "analyze_image returns analysis result" do
    OllamaStubs.setup_image_analysis_stub

    result = @service.analyze_image(@inventory_item.photo)

    assert result.success?, "Analysis should succeed"
    assert result.response.present?, "Should return analysis response"
    assert result.model_used == "llava", "Should specify model used"
    assert result.processing_time_ms > 0, "Should track processing time"
  end

  test "analyze_image handles API errors gracefully" do
    OllamaStubs.setup_image_analysis_error_stub

    result = @service.analyze_image(@inventory_item.photo)

    assert_not result.success?, "Analysis should fail"
    assert result.error.present?, "Should return error message"
  end

  test "analyze_image handles connection errors" do
    OllamaStubs.setup_ollama_unavailable_stub

    result = @service.analyze_image(@inventory_item.photo)

    assert_not result.success?, "Analysis should fail"
    assert result.error.present?, "Should return error message"
  end

  test "analyze_image with custom prompt" do
    OllamaStubs.setup_image_analysis_stub

    custom_prompt = "Describe the style and occasion suitability of this clothing item"
    result = @service.analyze_image(@inventory_item.photo, prompt: custom_prompt)

    assert result.success?, "Analysis should succeed"
    # The service should use the custom prompt
  end

  test "analyze_image caches results by image hash" do
    OllamaStubs.setup_image_analysis_stub

    # First analysis
    result1 = @service.analyze_image(@inventory_item.photo)
    assert result1.success?

    # Second analysis with same image should use cache
    result2 = @service.analyze_image(@inventory_item.photo)
    assert result2.success?
    assert_equal result1.response, result2.response, "Should return cached result"
  end

  test "analyze_image bypasses cache when forced" do
    OllamaStubs.setup_image_analysis_stub

    # First analysis
    result1 = @service.analyze_image(@inventory_item.photo)
    assert result1.success?

    # Force re-analysis
    result2 = @service.analyze_image(@inventory_item.photo, force: true)
    assert result2.success?
    # Results might be different due to AI variability
  end

  test "analyze_image validates image format" do
    # Create item with invalid image
    item = create(:clothing_item)
    item.photo.attach(
      io: StringIO.new("not_an_image"),
      filename: "test.txt",
      content_type: "text/plain"
    )

    result = @service.analyze_image(item.photo)

    assert_not result.success?, "Should fail for invalid image"
    assert result.error.include?("Invalid image format"), "Should return format error"
  end

  test "analyze_image handles large images" do
    # Mock large image
    large_image = StringIO.new("x" * (15.megabytes))
    @inventory_item.photo.attach(
      io: large_image,
      filename: "large.jpg",
      content_type: "image/jpeg"
    )

    OllamaStubs.setup_image_analysis_stub

    result = @service.analyze_image(@inventory_item.photo)

    assert result.success?, "Should handle large images"
  end

  test "analyze_image returns structured data" do
    OllamaStubs.setup_image_analysis_stub({
      "model" => "llava",
      "created_at" => "2025-01-25T10:30:00Z",
      "response" => "This is a blue cotton t-shirt with a casual style. It appears to be a basic crew neck design suitable for everyday wear.",
      "done" => true
    })

    result = @service.analyze_image(@inventory_item.photo)

    assert result.success?
    assert result.response.include?("blue cotton t-shirt"), "Should contain analysis text"
    assert result.model_used == "llava", "Should track model"
    assert result.confidence_score.present?, "Should have confidence score"
  end

  test "analyze_image handles timeout" do
    # Mock timeout
    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_timeout

    result = @service.analyze_image(@inventory_item.photo)

    assert_not result.success?, "Should handle timeout"
    assert result.error.include?("timeout"), "Should return timeout error"
  end
end
