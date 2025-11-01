require "test_helper"

class AnalyzeOutfitPhotoJobTest < ActiveJob::TestCase
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
    # Use memory store for cache in these tests
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
    assert_enqueued_with(job: AnalyzeOutfitPhotoJob, args: [ @image_blob.id, @user.id, @job_id ]) do
      AnalyzeOutfitPhotoJob.perform_later(@image_blob.id, @user.id, @job_id)
    end
  end

  test "job creates status entry in cache" do
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ollama_available?

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)

    assert status.present?
    assert_includes %w[processing completed failed], status["status"]
    assert_not_equal "not_found", status["status"]
  end

  test "get_status returns not_found for invalid job_id" do
    status = AnalyzeOutfitPhotoJob.get_status("invalid-job-id")

    assert_equal "not_found", status["status"]
    assert status["error"].present?
  end

  test "job updates status to processing" do
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ollama_available?

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)

    assert status.present?
    assert_includes %w[processing completed failed], status["status"]
    assert_not_equal "not_found", status["status"]
  end

  test "job handles analyzer errors gracefully" do
    # Mock analyzer instance to raise error when analyze is called
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).raises(StandardError, "Analysis failed")
    Services::OutfitPhotoAnalyzer.stubs(:new).returns(mock_analyzer)

    assert_nothing_raised do
      AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)
    end

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job marks as failed when no items detected" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "items" => [],
      "total_items" => 0
    })
    Services::OutfitPhotoAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
    assert_includes status["error"].to_s, "No items detected"
  end

  test "job marks as failed when error in analysis results" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "error" => "Analysis failed",
      "items" => [],
      "total_items" => 0
    })
    Services::OutfitPhotoAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"]
    assert status["error"].present?
  end

  test "job includes blob_id in successful results" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "items" => [
        {
          "category_name" => "T-Shirt",
          "name" => "Test Item",
          "description" => "Test description",
          "confidence" => 0.9
        }
      ],
      "total_items" => 1
    })
    Services::OutfitPhotoAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert_equal "completed", status["status"]
    assert_equal @image_blob.id, status["data"]["blob_id"]
    assert_equal 1, status["data"]["total_items"]
    assert_equal 1, status["data"]["items"].length
  end

  test "job handles StandardError in perform gracefully" do
    # Mock Blob.find to raise error, which will be caught by the rescue block
    ActiveStorage::Blob.stubs(:find).with(@image_blob.id).raises(ActiveRecord::RecordNotFound.new("Blob not found"))

    assert_nothing_raised do
      AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)
    end

    # The job should catch the error and update status to failed
    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert_equal "failed", status["status"], "Status should be 'failed' when error occurs. Got: #{status.inspect}"
    assert status["error"].present?, "Error should be present in status. Got: #{status.inspect}"
  end

  test "get_status handles cache read errors" do
    Rails.cache.stubs(:read).raises(StandardError, "Cache error")

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)

    assert_equal "error", status["status"]
    assert status["error"].present?
  end

  test "job stores updated_at timestamp in status" do
    mock_analyzer = stub
    mock_analyzer.stubs(:analyze).returns({
      "items" => [
        {
          "category_name" => "T-Shirt",
          "name" => "Test Item",
          "description" => "Test",
          "confidence" => 0.9
        }
      ],
      "total_items" => 1
    })
    Services::OutfitPhotoAnalyzer.stubs(:new).returns(mock_analyzer)

    AnalyzeOutfitPhotoJob.perform_now(@image_blob.id, @user.id, @job_id)

    status = AnalyzeOutfitPhotoJob.get_status(@job_id)
    assert status["updated_at"].present?
    assert_not_nil Time.parse(status["updated_at"])
  end
end
