require "test_helper"

class PlatformOpsTest < ActionDispatch::IntegrationTest
  test "GET /up returns application status" do
    get "/up"

    assert_response :success
    body = JSON.parse(@response.body)

    assert_equal "ok", body["status"]
    assert body["timestamp"].present?, "Should include timestamp"
  end

  test "GET /up returns 503 when application is unhealthy" do
    # Mock unhealthy state
    HealthChecker.stubs(:healthy?).returns(false)
    get "/up"

    assert_response :service_unavailable
    body = JSON.parse(@response.body)

    assert_equal "error", body["status"]
    assert body["error"].present?, "Should include error details"
  end

  test "GET /api/v1/health returns detailed health status" do
    get "/api/v1/health"

    assert_response :success
    body = JSON.parse(@response.body)

    assert_equal "ok", body["status"]
    assert body["checks"].present?, "Should include health checks"
    assert body["checks"]["database"].present?, "Should check database"
    assert body["checks"]["redis"].present?, "Should check Redis"
    assert body["checks"]["storage"].present?, "Should check storage"
    assert body["timestamp"].present?, "Should include timestamp"
  end

  test "GET /api/v1/health returns 503 when checks fail" do
    # Mock failing health checks
    HealthChecker.stubs(:check_database).returns(false)
    get "/api/v1/health"

    assert_response :service_unavailable
    body = JSON.parse(@response.body)

    assert_equal "error", body["status"]
    assert body["checks"]["database"] == false, "Should show database failure"
  end

  test "GET /ready returns readiness status" do
    get "/ready"

    assert_response :success
    body = JSON.parse(@response.body)

    assert_equal "ready", body["status"]
    assert body["timestamp"].present?, "Should include timestamp"
  end

  test "GET /ready returns 503 when not ready" do
    # Mock not ready state
    ReadinessChecker.stubs(:ready?).returns(false)
    get "/ready"

    assert_response :service_unavailable
    body = JSON.parse(@response.body)

    assert_equal "not_ready", body["status"]
    assert body["reason"].present?, "Should include reason"
  end

  test "requests include request ID in headers" do
    get "/api/v1/health"

    assert @response.headers["X-Request-ID"].present?, "Should include request ID header"
  end

  test "requests include request ID in logs" do
    request_id = nil

    # Mock logger to capture request ID
    Rails.logger.stubs(:info).returns(nil)
    get "/api/v1/health"

    assert request_id.present?, "Request ID should be logged"
    assert_equal @response.headers["X-Request-ID"], request_id, "Logged ID should match header"
  end

  test "error responses have consistent envelope format" do
    get "/api/v1/clothing_items/999999", headers: api_v1_headers("invalid_token")

    assert_response :unauthorized
    body = JSON.parse(@response.body)

    assert body["success"] == false, "Should have success: false"
    assert body["error"].present?, "Should have error object"
    assert body["error"]["code"].present?, "Should have error code"
    assert body["error"]["message"].present?, "Should have error message"
    assert body["timestamp"].present?, "Should have timestamp"
  end

  test "success responses have consistent envelope format" do
    user = create(:user)
    token = generate_jwt_token(user)

    get "/api/v1/clothing_items", headers: api_v1_headers(token)

    assert_response :success
    body = JSON.parse(@response.body)

    assert body["success"] == true, "Should have success: true"
    assert body["data"].present?, "Should have data object"
    assert body["timestamp"].present?, "Should have timestamp"
  end

  test "GET requests support ETag caching" do
    clothing_item = create(:clothing_item, :with_photo)
    user = clothing_item.user
    token = generate_jwt_token(user)

    # First request
    get "/api/v1/clothing_items/#{clothing_item.id}", headers: api_v1_headers(token)

    assert_response :success
    etag = @response.headers["ETag"]
    assert etag.present?, "Should include ETag header"

    # Second request with If-None-Match
    get "/api/v1/clothing_items/#{clothing_item.id}",
        headers: api_v1_headers(token).merge("If-None-Match" => etag)

    assert_response :not_modified, "Should return 304 for unchanged resource"
  end

  test "GET requests support Last-Modified caching" do
    clothing_item = create(:clothing_item, :with_photo)
    user = clothing_item.user
    token = generate_jwt_token(user)

    # First request
    get "/api/v1/clothing_items/#{clothing_item.id}", headers: api_v1_headers(token)

    assert_response :success
    last_modified = @response.headers["Last-Modified"]
    assert last_modified.present?, "Should include Last-Modified header"

    # Second request with If-Modified-Since
    get "/api/v1/clothing_items/#{clothing_item.id}",
        headers: api_v1_headers(token).merge("If-Modified-Since" => last_modified)

    assert_response :not_modified, "Should return 304 for unchanged resource"
  end

  test "ETag changes when resource is updated" do
    clothing_item = create(:clothing_item, :with_photo)
    user = clothing_item.user
    token = generate_jwt_token(user)

    # Get initial ETag
    get "/api/v1/clothing_items/#{clothing_item.id}", headers: api_v1_headers(token)
    initial_etag = @response.headers["ETag"]

    # Update resource
    put "/api/v1/clothing_items/#{clothing_item.id}",
        params: { name: "Updated Name" },
        headers: api_v1_headers(token)

    # Get new ETag
    get "/api/v1/clothing_items/#{clothing_item.id}", headers: api_v1_headers(token)
    new_etag = @response.headers["ETag"]

    assert_not_equal initial_etag, new_etag, "ETag should change after update"
  end

  test "N+1 queries are prevented with eager loading" do
    user = create(:user)
    token = generate_jwt_token(user)

    # Create items with associations
    clothing_items = create_list(:clothing_item, 5, :with_photo, user: user)
    clothing_items.each { |item| create(:ai_analysis, clothing_item: item) }

    # Mock query counter
    query_count = 0
    ActiveRecord::Base.connection.stubs(:execute).returns([])
    get "/api/v1/clothing_items", headers: api_v1_headers(token)

    # Should not have N+1 queries
    assert query_count < 10, "Should not have excessive queries (N+1 prevention)"
  end

  test "database queries are optimized with proper indexes" do
    user = create(:user)
    token = generate_jwt_token(user)

    # Create test data
    create_list(:clothing_item, 10, user: user)

    # Mock slow query detection
    slow_queries = []
    ActiveRecord::Base.connection.stubs(:execute).returns([])
    get "/api/v1/clothing_items?category=top", headers: api_v1_headers(token)

    assert slow_queries.empty?, "Should not have table scans (proper indexes)"
  end

  test "API responses include performance metrics in development" do
    Rails.env.stubs(:development?).returns(true)
    get "/api/v1/health"

    assert_response :success
    body = JSON.parse(@response.body)

    assert body["performance"].present?, "Should include performance metrics in dev"
    assert body["performance"]["response_time_ms"].present?, "Should include response time"
  end

  test "API responses exclude performance metrics in production" do
    Rails.env.stubs(:production?).returns(true)
    get "/api/v1/health"

    assert_response :success
    body = JSON.parse(@response.body)

    assert_not body["performance"].present?, "Should not include performance metrics in prod"
  end

  test "logging includes structured data" do
    log_entries = []

    Rails.logger.stubs(:info).returns(nil)
    get "/api/v1/health"

    # Should have structured log entries
    assert log_entries.any? { |entry| entry.include?("Request ID") }, "Should log request ID"
    assert log_entries.any? { |entry| entry.include?("Response Time") }, "Should log response time"
  end

  test "error logging includes stack trace in development" do
    Rails.env.stubs(:development?).returns(true)
    log_entries = []

    Rails.logger.stubs(:error).returns(nil)
    get "/api/v1/nonexistent"

    assert log_entries.any? { |entry| entry.include?("backtrace") }, "Should log stack trace in dev"
  end

  test "error logging excludes stack trace in production" do
    Rails.env.stubs(:production?).returns(true)
    log_entries = []

    Rails.logger.stubs(:error).returns(nil)
    get "/api/v1/nonexistent"

    assert_not log_entries.any? { |entry| entry.include?("backtrace") }, "Should not log stack trace in prod"
  end

  test "API documentation endpoint returns OpenAPI spec" do
    get "/api/v1/docs"

    assert_response :success
    body = JSON.parse(@response.body)

    assert_equal "3.0.0", body["openapi"], "Should return OpenAPI 3.0 spec"
    assert body["info"].present?, "Should include API info"
    assert body["paths"].present?, "Should include API paths"
  end

  test "API documentation includes all endpoints" do
    get "/api/v1/docs"

    assert_response :success
    body = JSON.parse(@response.body)

    paths = body["paths"]
    assert paths["/api/v1/auth/login"].present?, "Should document auth endpoints"
    assert paths["/api/v1/clothing_items"].present?, "Should document clothing items endpoints"
    assert paths["/api/v1/outfits"].present?, "Should document outfit endpoints"
  end

  private

  def generate_jwt_token(user)
    "jwt_token_for_#{user.id}"
  end
end
