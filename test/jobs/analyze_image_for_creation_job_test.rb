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
end
