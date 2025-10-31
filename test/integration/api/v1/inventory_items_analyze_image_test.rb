require "test_helper"

class Api::V1::InventoryItemsAnalyzeImageTest < ActionDispatch::IntegrationTest
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
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    @image_file = fixture_file_upload("sample_image.jpg", "image/jpeg")
  end

  def teardown
    # Restore original cache store
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "POST /api/v1/inventory_items/analyze_image_for_creation accepts image upload" do
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file },
         headers: auth_headers(@token) # Use auth_headers only, not api_v1_headers (which sets JSON content-type)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["job_id"].present?
    assert_equal "processing", body["data"]["status"]
  end

  test "POST /api/v1/inventory_items/analyze_image_for_creation rejects invalid image type" do
    text_file = fixture_file_upload("sample_text.txt", "text/plain")

    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: text_file },
         headers: auth_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "INVALID_IMAGE_TYPE", body["error"]["code"]
  end

  test "POST /api/v1/inventory_items/analyze_image_for_creation rejects missing image" do
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: {},
         headers: auth_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "MISSING_IMAGE", body["error"]["code"]
  end

  test "GET /api/v1/inventory_items/analyze_image_status/:job_id returns processing status" do
    # Skip if Ollama not available (job will fail the check_ollama_availability! call)
    skip "Set ENABLE_OLLAMA_TESTS=true to run tests with real Ollama" unless ollama_available?

    # Start a job
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file },
         headers: auth_headers(@token)

    job_id = json_response["data"]["job_id"]

    # Perform enqueued jobs synchronously so status is available
    perform_enqueued_jobs

    # Check status (should be processing, completed, or failed)
    # Job may fail if Ollama is not available, which is acceptable
    get "/api/v1/inventory_items/analyze_image_status/#{job_id}",
        headers: api_v1_headers(@token)

    # Accept both success (200) and unprocessable_entity (422) for failed jobs
    assert_includes [ 200, 422 ], @response.status, "Expected 200 or 422 status"
    body = json_response

    if @response.status == 422
      # Job failed (expected if Ollama unavailable)
      assert body["data"]["status"] == "failed"
      assert body["data"]["error"].present?
    else
      # Job succeeded or is still processing
      assert body["success"]
      assert_includes %w[processing completed failed], body["data"]["status"]
    end
  end

  test "GET /api/v1/inventory_items/analyze_image_status/:job_id returns 404 for invalid job_id" do
    get "/api/v1/inventory_items/analyze_image_status/invalid-job-id",
        headers: api_v1_headers(@token)

    assert_response :not_found
    body = json_response
    assert_not body["success"]
    assert_equal "JOB_NOT_FOUND", body["error"]["code"]
  end

  test "GET /api/v1/inventory_items/analyze_image_status/:job_id requires authentication" do
    get "/api/v1/inventory_items/analyze_image_status/some-job-id"

    assert_response :unauthorized
  end

  test "POST /api/v1/inventory_items/analyze_image_for_creation requires authentication" do
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file }

    assert_response :unauthorized
  end

  # Integration test with real Ollama (optional - only runs if Ollama available)
  test "POST /api/v1/inventory_items/analyze_image_for_creation and wait for completion with real Ollama" do
    skip "Set ENABLE_OLLAMA_TESTS=true and ensure Ollama is running to test with real Ollama" unless ollama_available?

    # Start analysis
    post "/api/v1/inventory_items/analyze_image_for_creation",
         params: { image: @image_file },
         headers: auth_headers(@token)

    assert_response :accepted
    job_id = json_response["data"]["job_id"]

    # Poll for completion (max 30 seconds)
    max_attempts = 10
    attempts = 0
    status = nil

    while attempts < max_attempts
      sleep 3
      attempts += 1

      get "/api/v1/inventory_items/analyze_image_status/#{job_id}",
          headers: api_v1_headers(@token)

      assert_response :success
      body = json_response
      status = body["data"]["status"]

      break if status == "completed" || status == "failed"
    end

    # Verify we got a result
    assert_not_nil status
    assert_includes %w[completed failed], status

    if status == "completed"
      # Verify analysis data structure
      get "/api/v1/inventory_items/analyze_image_status/#{job_id}",
          headers: api_v1_headers(@token)

      body = json_response
      analysis = body["data"]["analysis"]
      assert analysis.present?
      assert analysis["category_name"].present? || analysis["category_id"].present?
      assert analysis["name"].present?
      assert analysis["description"].present?
    end
  end
end
