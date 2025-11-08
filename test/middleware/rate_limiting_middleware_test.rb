require "test_helper"

class RateLimitingMiddlewareTest < ActiveSupport::TestCase
  def setup
    @app = ->(env) { [ 200, { "Content-Type" => "text/plain" }, [ "OK" ] ] }
    @middleware = RateLimitingMiddleware.new(@app)
    @env = Rack::MockRequest.env_for("/api/v1/health")

    # Use memory store for rate limiting tests (test env uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new
    Rails.cache.clear

    # Enable rate limiting in tests
    ENV["ENABLE_RATE_LIMITING"] = "true"
  end

  def teardown
    ENV.delete("ENABLE_RATE_LIMITING")
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "allows requests under rate limit" do
    status, headers, _body = @middleware.call(@env)

    assert_equal 200, status
    assert_not_nil headers["X-RateLimit-Limit"]
    assert_not_nil headers["X-RateLimit-Remaining"]
  end

  test "blocks requests exceeding authentication rate limit" do
    # Set up authentication endpoint
    env = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    request = ActionDispatch::Request.new(env)

    # Get the actual identifier that will be used
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:authentication]

    # Set count to exactly the limit (5 requests per minute)
    # Next request should be blocked
    cache_key = "rate_limit:authentication:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

    status, headers, body = @middleware.call(env)

    assert_equal 429, status
    assert_equal "0", headers["X-RateLimit-Remaining"]
    assert_equal config[:limit].to_s, headers["X-RateLimit-Limit"]
    assert_not_nil headers["Retry-After"]

    response_body = JSON.parse(body.first)
    assert_equal "RATE_LIMIT_EXCEEDED", response_body["error"]["code"]
  end

  test "blocks requests exceeding AI processing rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:ai_processing]

    # Set count to exactly the limit (10 requests per hour)
    cache_key = "rate_limit:ai_processing:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

    status, _headers, _body = @middleware.call(env)

    assert_equal 429, status
  end

  test "blocks requests exceeding file upload rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/primary_image", method: "POST",
                                    "CONTENT_TYPE" => "multipart/form-data")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:file_upload]

    # Set count to exactly the limit (20 requests per hour)
    cache_key = "rate_limit:file_upload:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

    status, _headers, _body = @middleware.call(env)

    assert_equal 429, status
  end

  test "uses standard rate limit for CRUD endpoints" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    status, headers, _body = @middleware.call(env)

    assert_equal 200, status
    assert_equal "100", headers["X-RateLimit-Limit"] # Standard limit
  end

  test "identifies user by JWT token when available" do
    user = create(:user)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer #{token}")

    # Test the identifier extraction method directly
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)

    # Should extract user ID from token
    assert_match(/^user:\d+$/, identifier, "Should identify user from JWT token")
  end

  test "falls back to IP address when no token" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    middleware = RateLimitingMiddleware.new(@app)
    request = ActionDispatch::Request.new(env)
    identifier = middleware.send(:get_identifier, request)

    assert_match(/^ip:/, identifier)
  end

  test "skips rate limiting for non-API requests" do
    env = Rack::MockRequest.env_for("/health")
    status, _headers, _body = @middleware.call(env)

    assert_equal 200, status
  end

  test "skips rate limiting in test environment by default" do
    # Temporarily disable rate limiting
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV.delete("ENABLE_RATE_LIMITING")

    env = Rack::MockRequest.env_for("/api/v1/health")
    status, _headers, _body = @middleware.call(env)

    assert_equal 200, status
  ensure
    ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
  end

  test "adds rate limit headers to successful responses" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    status, headers, _body = @middleware.call(env)

    assert_equal 200, status
    assert_not_nil headers["X-RateLimit-Limit"]
    assert_not_nil headers["X-RateLimit-Remaining"]
    assert_not_nil headers["X-RateLimit-Reset"]
  end

  test "determines endpoint type correctly for authentication" do
    middleware = RateLimitingMiddleware.new(@app)

    login_env = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    login_request = ActionDispatch::Request.new(login_env)
    assert_equal :authentication, middleware.send(:determine_endpoint_type, login_request)

    register_env = Rack::MockRequest.env_for("/api/v1/auth/register", method: "POST")
    register_request = ActionDispatch::Request.new(register_env)
    assert_equal :authentication, middleware.send(:determine_endpoint_type, register_request)
  end

  test "determines endpoint type correctly for AI processing" do
    middleware = RateLimitingMiddleware.new(@app)

    analyze_env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
    analyze_request = ActionDispatch::Request.new(analyze_env)
    assert_equal :ai_processing, middleware.send(:determine_endpoint_type, analyze_request)

    ai_env = Rack::MockRequest.env_for("/api/v1/ai/analyze", method: "POST")
    ai_request = ActionDispatch::Request.new(ai_env)
    assert_equal :ai_processing, middleware.send(:determine_endpoint_type, ai_request)
  end

  test "determines endpoint type correctly for file uploads" do
    middleware = RateLimitingMiddleware.new(@app)

    upload_env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/primary_image", method: "POST",
                                           "CONTENT_TYPE" => "multipart/form-data")
    upload_request = ActionDispatch::Request.new(upload_env)
    assert_equal :file_upload, middleware.send(:determine_endpoint_type, upload_request)
  end

  test "determines endpoint type correctly for standard CRUD" do
    middleware = RateLimitingMiddleware.new(@app)

    crud_env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    crud_request = ActionDispatch::Request.new(crud_env)
    assert_equal :standard, middleware.send(:determine_endpoint_type, crud_request)
  end
end
