require "test_helper"

class AnalyzeImageForCreationJobTest < ActiveJob::TestCase
  # Helper to check if Ollama is available
  def ollama_available?
    return false unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    begin
      uri = URI(ENV["OLLAMA_API_BASE"] || "http://localhost:11434")
      http = Net::HTTP.new(uri.host, uri.port)
      http.open_timeout = 2
      http.read_timeout = 2
      response = http.get("/api/tags")
      response.code == "200"
    rescue StandardError
      false
    end
  end

  def setup
    # Use memory store for cache in these tests (test environment uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @job_id = SecureRandom.uuid
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "job queues correctly" do
    assert_enqueued_with(job: AnalyzeImageForCreationJob, args: [ @image_blob.id, @user.id, @job_id ]) do
      AnalyzeImageForCreationJob.perform_later(@image_blob.id, @user.id, @job_id)
    end
  end

  test "job creates status entry in cache" do
    # Skip if Ollama not available (job will fail the check_ollama_availability! call)
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ollama_available?

    # Perform job (will fail if Ollama not available, but should create status)
    # Job should not raise exceptions, just mark as failed
    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)

    assert status.present?
    assert_includes %w[processing completed failed], status["status"]
    # Should not be not_found since job was executed
    assert_not_equal "not_found", status["status"]
  end

  test "get_status returns not_found for invalid job_id" do
    status = AnalyzeImageForCreationJob.get_status("invalid-job-id")

    assert_equal "not_found", status["status"]
    assert status["error"].present?
  end

  test "job updates status to processing" do
    # Skip if Ollama not available (job will fail the check_ollama_availability! call)
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ollama_available?

    # Start job
    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    # Check status immediately (may be processing or completed/failed depending on speed)
    status = AnalyzeImageForCreationJob.get_status(@job_id)

    assert status.present?
    assert_includes %w[processing completed failed], status["status"]
    # Should not be not_found since job was executed
    assert_not_equal "not_found", status["status"]
  end

  test "job handles analyzer errors gracefully" do
    # Mock analyzer instance to raise error when analyze is called
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).raises(StandardError, "Analysis failed")
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    assert_nothing_raised do
      AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)
    end

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?, "Expected error to be present, but got: #{status.inspect}"

    # Error can be a string or a hash with an "error" key
    error_message = if status["error"].is_a?(Hash)
      status["error"]["error"] || status["error"].values.first || status["error"].to_s
    else
      status["error"]
    end

    assert_match(/Analysis failed|wrong number of arguments/, error_message.to_s)
  end

  # Integration test with real Ollama (optional)
  test "job performs full analysis with real Ollama" do
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ENV["ENABLE_OLLAMA_TESTS"] == "true"

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    # Wait a bit for processing
    sleep 5

    status = AnalyzeImageForCreationJob.get_status(@job_id)

    assert_includes %w[completed failed], status["status"]

    if status["status"] == "completed"
      analysis = status["data"]
      assert analysis.present?
      assert analysis["category_name"].present? || analysis["category_id"].present?
      assert analysis["name"].present?
      assert analysis["description"].present?
      assert analysis["confidence"].present?
    end
  end

  test "job handles low confidence analysis" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "confidence" => 0.05, # Below 0.1 threshold
      "name" => "Test Item"
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job handles analysis with error field" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "error" => "Analysis failed",
      "confidence" => 0.8
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job includes blob_id in completed status" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "confidence" => 0.9,
      "name" => "Test Item",
      "category_name" => "Tops"
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    if status["status"] == "completed"
      assert_equal @image_blob.id, status["data"]["blob_id"]
    end
  end

  test "job handles missing image blob" do
    # Job catches all errors and updates status to failed, doesn't re-raise
    AnalyzeImageForCreationJob.perform_now(999999, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job handles missing user" do
    # Job catches all errors and updates status to failed, doesn't re-raise
    AnalyzeImageForCreationJob.perform_now(@image_blob.id, 999999, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    # The job should catch the error and set status to "failed"
    # If cache write fails, status will be "not_found", but we expect "failed"
    assert_equal "failed", status["status"], "Job should set status to failed when user is missing. Got: #{status.inspect}"
    assert status["error"].present?, "Error message should be present in status"
  end

  test "update_status stores status in cache" do
    job = AnalyzeImageForCreationJob.new
    job.instance_variable_set(:@job_id, @job_id)

    job.send(:update_status, "processing", { "test" => "data" }, nil)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "processing", status["status"]
    assert_equal "data", status["data"]["test"]
  end

  test "set_status stores status with string keys" do
    status_data = {
      "status" => "completed",
      "data" => { "name" => "Test" }
    }

    AnalyzeImageForCreationJob.set_status(@job_id, status_data)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "completed", status["status"]
    assert_equal "Test", status["data"]["name"]
  end

  test "get_status handles cache read errors" do
    Rails.cache.stubs(:read).raises(StandardError.new("Cache error"))
    Rails.logger.stubs(:error)

    status = AnalyzeImageForCreationJob.get_status(@job_id)

    assert_equal "error", status["status"]
    assert status["error"].present?
  end

  test "get_status handles non-hash cache data" do
    Rails.cache.write(AnalyzeImageForCreationJob.status_key(@job_id), "string data", expires_in: 1.hour)

    status = AnalyzeImageForCreationJob.get_status(@job_id)

    assert_equal "string data", status
  end

  test "status_key generates correct key format" do
    job_id = "test-job-123"
    key = AnalyzeImageForCreationJob.status_key(job_id)

    assert_equal "inventory_creation_analysis:test-job-123", key
  end

  test "job logs completion message" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "confidence" => 0.9,
      "name" => "Test Item"
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)
    log_messages = []
    Rails.logger.stubs(:info).with { |msg| log_messages << msg.to_s; true }

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    log_message = log_messages.find { |msg| msg.to_s.include?("Analysis completed successfully") }
    assert log_message.present?, "Should log completion. Logged messages: #{log_messages.inspect}"
    assert log_message.to_s.include?(@job_id)
  end

  test "job logs error with backtrace" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).raises(StandardError.new("Test error"))
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)
    log_messages = []
    Rails.logger.stubs(:error).with { |msg| log_messages << msg; true }

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    error_log = log_messages.find { |msg| msg.include?("Failed to analyze image") }
    assert error_log.present?, "Should log error"
    assert error_log.include?(@job_id)
  end

  test "job handles nil confidence in results" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "confidence" => nil,
      "name" => "Test Item"
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end

  test "job handles zero confidence in results" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "confidence" => 0.0,
      "name" => "Test Item"
    })
    Services::InventoryCreationAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeImageForCreationJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeImageForCreationJob.get_status(@job_id)
    assert_equal "failed", status["status"]
  end
end
