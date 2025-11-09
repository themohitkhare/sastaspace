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
    Rails.cache.clear if Rails.cache.respond_to?(:clear)
    ENV.delete("ENABLE_RATE_LIMITING")
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "allows requests under rate limit" do
    # Ensure rate limiting is enabled for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
      status, headers, _body = @middleware.call(@env)

      assert_equal 200, status
      assert_not_nil headers["X-RateLimit-Limit"]
      assert_not_nil headers["X-RateLimit-Remaining"]
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
  end

  test "blocks requests exceeding authentication rate limit" do
    # Ensure rate limiting is enabled and cache is clean for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
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
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
  end

  test "blocks requests exceeding AI processing rate limit" do
    # Ensure rate limiting is enabled and cache is clean for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
      env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
      request = ActionDispatch::Request.new(env)
      identifier = @middleware.send(:get_identifier, request)
      config = RateLimitingMiddleware::RATE_LIMITS[:ai_processing]

      # Set count to exactly the limit (10 requests per hour)
      cache_key = "rate_limit:ai_processing:#{identifier}:#{config[:period]}"
      Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

      status, _headers, _body = @middleware.call(env)

      assert_equal 429, status
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
  end

  test "blocks requests exceeding file upload rate limit" do
    # Ensure rate limiting is enabled and cache is clean for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
      env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/primary_image", method: "POST",
                                      "CONTENT_TYPE" => "multipart/form-data")

      # Create request object to get identifier and endpoint type
      request = ActionDispatch::Request.new(env)
      identifier = @middleware.send(:get_identifier, request)
      endpoint_type = @middleware.send(:determine_endpoint_type, request)
      config = RateLimitingMiddleware::RATE_LIMITS[:file_upload]

      # Verify endpoint type is correctly determined
      assert_equal :file_upload, endpoint_type, "Endpoint should be identified as file_upload"

      # Set count to exactly the limit (20 requests per hour)
      # The middleware checks: current_count >= config[:limit]
      # So setting it to the limit means the next request (which would make it 21) should be blocked
      cache_key = "rate_limit:#{endpoint_type}:#{identifier}:#{config[:period]}"
      Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

      # Verify cache was set correctly
      cached_value = Rails.cache.read(cache_key)
      assert_equal config[:limit], cached_value, "Cache should contain the limit value"

      # Double-check: verify the middleware will use the same identifier
      # by creating a new request from the same env
      middleware_request = ActionDispatch::Request.new(env)
      middleware_identifier = @middleware.send(:get_identifier, middleware_request)
      middleware_endpoint_type = @middleware.send(:determine_endpoint_type, middleware_request)
      middleware_cache_key = "rate_limit:#{middleware_endpoint_type}:#{middleware_identifier}:#{config[:period]}"

      assert_equal identifier, middleware_identifier, "Identifiers should match"
      assert_equal endpoint_type, middleware_endpoint_type, "Endpoint types should match"
      assert_equal cache_key, middleware_cache_key, "Cache keys should match"

      # Verify the cache value is still there
      assert_equal config[:limit], Rails.cache.read(cache_key), "Cache should still contain the limit value"

      status, _headers, _body = @middleware.call(env)

      assert_equal 429, status, "Should return 429 when rate limit is exceeded"
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
      Rails.cache.clear
    end
  end

  test "uses standard rate limit for CRUD endpoints" do
    # Ensure rate limiting is enabled for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
      env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
      status, headers, _body = @middleware.call(env)

      assert_equal 200, status
      assert_equal "100", headers["X-RateLimit-Limit"] # Standard limit
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
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
    # Ensure rate limiting is enabled for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"

    begin
      env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
      status, headers, _body = @middleware.call(env)

      assert_equal 200, status
      assert_not_nil headers["X-RateLimit-Limit"]
      assert_not_nil headers["X-RateLimit-Remaining"]
      assert_not_nil headers["X-RateLimit-Reset"]
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
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

  test "skips rate limiting when DISABLE_RATE_LIMITING is set" do
    original_value = ENV["DISABLE_RATE_LIMITING"]
    ENV["DISABLE_RATE_LIMITING"] = "true"

    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    status, _headers, _body = @middleware.call(env)

    assert_equal 200, status
  ensure
    ENV["DISABLE_RATE_LIMITING"] = original_value if original_value
  end

  test "handles invalid JWT token gracefully" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer invalid_token")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)

    # Should fall back to IP when token is invalid
    assert_match(/^ip:/, identifier)
  end

  test "handles expired JWT token gracefully" do
    # Create an expired token by encoding with a past expiration
    # The JWT library will decode it but it will be expired
    expired_token = Auth::JsonWebToken.encode_access_token(user_id: 1, exp: 1.hour.ago.to_i)

    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer #{expired_token}")
    request = ActionDispatch::Request.new(env)

    # Stub the decode to raise an exception (simulating expired token)
    Auth::JsonWebToken.stubs(:decode).raises(JWT::ExpiredSignature.new("Token expired"))

    identifier = @middleware.send(:get_identifier, request)

    # Should fall back to IP when token is expired
    assert_match(/^ip:/, identifier)
  ensure
    Auth::JsonWebToken.unstub(:decode) if Auth::JsonWebToken.respond_to?(:unstub)
  end

  test "handles missing remote_ip by using unknown" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    request = ActionDispatch::Request.new(env)
    request.stubs(:remote_ip).returns(nil)
    identifier = @middleware.send(:get_identifier, request)

    assert_equal "ip:unknown", identifier
  end

  test "determines endpoint type for outfits analyze" do
    middleware = RateLimitingMiddleware.new(@app)
    env = Rack::MockRequest.env_for("/api/v1/outfits/analyze", method: "POST")
    request = ActionDispatch::Request.new(env)
    assert_equal :ai_processing, middleware.send(:determine_endpoint_type, request)
  end

  test "determines endpoint type for additional_images upload" do
    middleware = RateLimitingMiddleware.new(@app)
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/additional_images", method: "POST")
    request = ActionDispatch::Request.new(env)
    assert_equal :file_upload, middleware.send(:determine_endpoint_type, request)
  end

  test "determines endpoint type for analyze_photo endpoint" do
    middleware = RateLimitingMiddleware.new(@app)
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/analyze_photo", method: "POST")
    request = ActionDispatch::Request.new(env)
    # analyze_photo matches the AI processing pattern first (contains "analyze")
    assert_equal :ai_processing, middleware.send(:determine_endpoint_type, request)
  end

  test "determines endpoint type for analyze_image_for_creation endpoint" do
    middleware = RateLimitingMiddleware.new(@app)
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
    request = ActionDispatch::Request.new(env)
    # analyze_image_for_creation matches the AI processing pattern first (contains "analyze")
    assert_equal :ai_processing, middleware.send(:determine_endpoint_type, request)
  end

  test "determines endpoint type for POST with multipart content type" do
    middleware = RateLimitingMiddleware.new(@app)
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "POST",
                                    "CONTENT_TYPE" => "multipart/form-data; boundary=----WebKitFormBoundary")
    request = ActionDispatch::Request.new(env)
    assert_equal :file_upload, middleware.send(:determine_endpoint_type, request)
  end

  test "rate_limit_exceeded logs warning" do
    env = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:authentication]

    cache_key = "rate_limit:authentication:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, config[:limit], expires_in: config[:period].seconds)

    Rails.logger.expects(:warn).with(regexp_matches(/Rate limit exceeded/))
    @middleware.send(:rate_limit_exceeded?, identifier, :authentication, config)
  end

  test "add_rate_limit_headers calculates remaining correctly" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:standard]

    # Set count to 50
    cache_key = "rate_limit:standard:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, 50, expires_in: config[:period].seconds)

    headers = {}
    @middleware.send(:add_rate_limit_headers, headers, identifier, :standard, config)

    assert_equal "50", headers["X-RateLimit-Remaining"] # 100 - 50 = 50
  end

  test "add_rate_limit_headers sets remaining to 0 when over limit" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    request = ActionDispatch::Request.new(env)
    identifier = @middleware.send(:get_identifier, request)
    config = RateLimitingMiddleware::RATE_LIMITS[:standard]

    # Set count to 150 (over limit)
    cache_key = "rate_limit:standard:#{identifier}:#{config[:period]}"
    Rails.cache.write(cache_key, 150, expires_in: config[:period].seconds)

    headers = {}
    @middleware.send(:add_rate_limit_headers, headers, identifier, :standard, config)

    assert_equal "0", headers["X-RateLimit-Remaining"] # Should be 0, not negative
  end

  test "increments rate limit counter on successful request" do
    # Ensure rate limiting is enabled for this test
    original_value = ENV["ENABLE_RATE_LIMITING"]
    ENV["ENABLE_RATE_LIMITING"] = "true"
    Rails.cache.clear

    begin
      env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
      request = ActionDispatch::Request.new(env)
      identifier = @middleware.send(:get_identifier, request)
      config = RateLimitingMiddleware::RATE_LIMITS[:standard]

      cache_key = "rate_limit:standard:#{identifier}:#{config[:period]}"
      initial_count = Rails.cache.read(cache_key) || 0

      @middleware.call(env)

      new_count = Rails.cache.read(cache_key)
      assert_equal initial_count + 1, new_count
    ensure
      ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    end
  end
end
