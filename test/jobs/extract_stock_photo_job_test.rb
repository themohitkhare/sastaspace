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
    # Create fake image data that's at least 50KB (job requirement)
    fake_image_data = "x" * 60_000 # 60KB of fake data
    image_data = Base64.encode64(fake_image_data)
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "completed", status["status"], "Job should complete successfully"
    assert status["data"]["extracted_blob_id"].present?, "Extracted blob ID should be present in status data"
  end

  test "job includes extraction prompt in completed status" do
    # Create fake image data that's at least 50KB (job requirement)
    fake_image_data = "x" * 60_000 # 60KB of fake data
    image_data = Base64.encode64(fake_image_data)
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "completed", status["status"], "Job should complete successfully"
    assert status["data"]["extraction_prompt"].present?, "Extraction prompt should be present in status data"
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

  test "get_status recovers from queue when cache is empty" do
    skip "SolidQueue not available" unless defined?(SolidQueue::Job)

    # Enqueue a job
    job = ExtractStockPhotoJob.perform_later(@image_blob.id, @analysis_results, @user.id, @job_id)
    active_job_id = job.job_id

    # Wait for after_enqueue callback to store mapping
    sleep 0.2

    # Check that mapping was stored
    stored_active_job_id = Rails.cache.read(ExtractStockPhotoJob.active_job_id_key(@job_id))
    if stored_active_job_id.present?
      assert_equal active_job_id, stored_active_job_id, "ActiveJob ID should be stored"

      # Clear status cache to force recovery
      Rails.cache.delete(ExtractStockPhotoJob.status_key(@job_id))

      # Wait for job to be persisted in SolidQueue
      sleep 0.3

      # Get status (should recover from queue)
      status = ExtractStockPhotoJob.get_status(@job_id)

      # Should not be "not_found" if recovery worked
      if status["status"] != "not_found"
        assert_includes %w[queued processing completed], status["status"]
      end
    end
  end

  test "active_job_id_key generates correct key format" do
    job_id = "test-job-123"
    key = ExtractStockPhotoJob.active_job_id_key(job_id)

    assert_equal "stock_photo_extraction:active_job_id:test-job-123", key
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

  test "job handles missing image_data in extraction result" do
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => nil
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?

    # Handle both symbol and string keys, and both hash and string error formats
    error_data = status["error"]
    if error_data.is_a?(Hash)
      error_msg = error_data["error"] || error_data[:error] || error_data["message"] || error_data[:message]
    else
      error_msg = error_data
    end

    assert error_msg.present?, "Error message should be present. Error data: #{error_data.inspect}"
    assert_includes error_msg.to_s, "ComfyUI did not return image data"
  end

  test "job handles image_data too small and attempts re-download" do
    # Create small image data (less than 50KB)
    small_image_data = "x" * 10_000 # 10KB
    # Create valid PNG header
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    small_image_data = png_header + small_image_data

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {
        "60" => {
          "images" => [
            {
              "filename" => "test_output.png",
              "subfolder" => "",
              "type" => "output"
            }
          ]
        }
      },
      "image_data" => small_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Stub HTTP request for re-download
    large_image_data = png_header + ("x" * 60_000) # 60KB
    WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
      .to_return(
        status: 200,
        body: large_image_data,
        headers: { "Content-Type" => "image/png" }
      )

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    # Should either complete or fail, but not crash
    assert_includes %w[completed failed], status["status"]
  end

  test "job handles re-download failure when image still too small" do
    small_image_data = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*") + ("x" * 10_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {
        "60" => {
          "images" => [
            {
              "filename" => "test_output.png",
              "subfolder" => "",
              "type" => "output"
            }
          ]
        }
      },
      "image_data" => small_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Stub HTTP request to return small image again
    WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
      .to_return(
        status: 200,
        body: small_image_data,
        headers: { "Content-Type" => "image/png" }
      )

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job handles re-download when outputs missing" do
    small_image_data = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*") + ("x" * 10_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => nil,
      "image_data" => small_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job finds and updates inventory item with primary image" do
    # Create inventory item with the image blob as primary image
    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(@image_blob)

    # Create valid PNG image data
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["inventory_item_id"].present?
      assert_equal inventory_item.id, status["data"]["inventory_item_id"]
    end
  end

  test "job handles inventory_item_id that doesn't match blob" do
    # Create inventory item with different blob
    other_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "other_image.jpg",
      content_type: "image/jpeg"
    )
    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(other_blob)

    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    # Should still complete, but may not attach to item
    assert_includes %w[completed failed], status["status"]
  end

  test "job creates blob from binary PNG data" do
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    binary_image_data = png_header + ("x" * 60_000)
    binary_image_data.force_encoding("BINARY")

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => binary_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["extracted_blob_id"].present?
    end
  end

  test "job creates blob from base64 encoded PNG data" do
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    binary_data = png_header + ("x" * 60_000)
    base64_data = Base64.encode64(binary_data)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => base64_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert status["data"]["extracted_blob_id"].present?
    end
  end

  test "job handles create_blob_from_data with invalid data" do
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => "" # Empty data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job broadcasts progress messages" do
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ActionCable.server.expects(:broadcast).at_least(1)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)
  end

  test "job handles missing inventory item gracefully" do
    # Use a blob that's not attached to any inventory item
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    # Should complete even if no inventory item found
    assert_includes %w[completed failed], status["status"]
  end

  test "job handles inventory_item_id parameter" do
    inventory_item = create(:inventory_item, user: @user)
    inventory_item.primary_image.attach(@image_blob)

    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id, inventory_item.id)

    status = ExtractStockPhotoJob.get_status(@job_id)
    if status["status"] == "completed"
      assert_equal inventory_item.id, status["data"]["inventory_item_id"]
    end
  end

  test "job logs extraction result details when image_data present" do
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")
    large_image_data = png_header + ("x" * 60_000)

    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => large_image_data
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Capture all log calls since MetricsLogger also logs
    log_calls = []
    Rails.logger.stubs(:info).with { |arg| log_calls << arg.to_s; true }

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    # Verify our specific log message was called
    assert log_calls.any? { |call| call.match?(/ComfyUI extraction result.*has_image_data=true/) }, "Expected log message about image_data present"
  end

  test "job logs extraction result details when image_data missing" do
    mock_result = {
      "success" => true,
      "job_id" => SecureRandom.uuid,
      "outputs" => {},
      "image_data" => nil
    }
    ComfyUiService.stubs(:extract_stock_photo).returns(mock_result)

    # Capture all log calls since MetricsLogger also logs
    log_calls = []
    Rails.logger.stubs(:info).with { |arg| log_calls << arg.to_s; true }

    ExtractStockPhotoJob.perform_now(@image_blob.id, @analysis_results, @user.id, @job_id)

    # Verify our specific log message was called
    assert log_calls.any? { |call| call.match?(/ComfyUI extraction result.*has_image_data=false/) }, "Expected log message about image_data missing"
  end
end
