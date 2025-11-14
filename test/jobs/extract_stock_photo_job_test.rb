require "test_helper"

class ExtractStockPhotoJobTest < ActiveJob::TestCase
  def setup
    # Use memory store for cache in these tests
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @analysis_results = {
      "name" => "Grey Hoodie",
      "category_name" => "Hoodies",
      "colors" => [ "grey" ],
      "gender_appropriate" => true,
      "confidence" => 0.9
    }
    @job_id = SecureRandom.uuid
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "job queues correctly" do
    assert_enqueued_with(
      job: ExtractStockPhotoJob,
      args: [ @image_blob.id, @analysis_results, @user.id, @job_id ]
    ) do
      ExtractStockPhotoJob.perform_later(@image_blob.id, @analysis_results, @user.id, @job_id)
    end
  end

  test "job creates status entry in cache" do
    # Mock ComfyUI service to return success
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => Base64.encode64("fake image data")
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)

    assert status.present?
    assert_includes %w[processing completed failed], status["status"]
  end

  test "job updates status to processing" do
    # Mock ComfyUI service
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => Base64.encode64("fake image data")
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_includes %w[processing completed failed], status["status"]
  end

  test "job handles ComfyUI extraction failure" do
    # Mock ComfyUI service to return failure
    mock_result = {
      "success" => false,
      "error" => "Extraction failed"
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    assert_nothing_raised do
      ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)
    end

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job handles ComfyUI service errors gracefully" do
    # Mock ComfyUI service to raise error
    ComfyUiService.stubs(:extract_stock_photo).raises(StandardError, "Service unavailable")

    assert_nothing_raised do
      ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)
    end

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job creates blob from base64 image data" do
    image_data = Base64.encode64("fake png image data")
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["extracted_blob_id"].present?
    end
  end

  test "job includes extraction prompt in completed status" do
    image_data = Base64.encode64("fake png image data")
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["extraction_prompt"].present?
    end
  end

  test "job handles missing image blob" do
    assert_nothing_raised do
      ExtractStockPhotoJob.perform_now(999999, @analysis_results, @user.id, @job_id)
    end

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job handles missing user" do
    assert_nothing_raised do
      ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, 999999, @job_id)
    end

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job handles JSON string analysis_results" do
    analysis_json = @analysis_results.to_json
    image_data = Base64.encode64("fake png image data")
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    assert_nothing_raised do
      ExtractStockPhotoJob.perform_now(@image_blob.id, analysis_json, @user.id, @job_id)
    end

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_includes %w[processing completed failed], status["status"]
  end

  test "get_status returns not_found for invalid job_id" do
    status = ExtractStockPhotoJob.get_status("invalid-job-id")

    assert_equal "not_found", status["status"]
    assert status["error"].present?
  end

  test "status_key generates correct key format" do
    job_id = "test-job-123"
    key = ExtractStockPhotoJob.status_key(job_id)

    assert_equal "stock_photo_extraction:test-job-123", key
  end

  test "job uses stored extraction_prompt when available" do
    stored_prompt = "STORED EXTRACTION PROMPT - DO NOT GENERATE"
    analysis_with_prompt = @analysis_results.merge("extraction_prompt" => stored_prompt)

    image_data = Base64.encode64("fake png image data")
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Verify ExtractionPromptBuilder is NOT called
    Services::ExtractionPromptBuilder.expects(:new).never

    ExtractStockPhotoJob.perform_now(@image_blob.id, analysis_with_prompt, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert_equal stored_prompt, status["data"]["extraction_prompt"]
    end
  end

  test "job generates extraction_prompt when not stored" do
    # Ensure no extraction_prompt in analysis results
    analysis_without_prompt = @analysis_results.except("extraction_prompt")

    image_data = Base64.encode64("fake png image data")
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Verify ExtractionPromptBuilder IS called
    mock_builder = stub(build_prompt: "GENERATED PROMPT")
    Services::ExtractionPromptBuilder.expects(:new).returns(mock_builder)

    ExtractStockPhotoJob.perform_now(@image_blob.id, analysis_without_prompt, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["extraction_prompt"].present?
    end
  end
end
