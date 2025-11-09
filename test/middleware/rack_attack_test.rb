require "test_helper"

class RackAttackTest < ActiveSupport::TestCase
  def setup
    # Use memory store for rate limiting tests (test env uses null_store by default)
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new
    Rails.cache.clear

    # Enable rate limiting in tests
    ENV["ENABLE_RATE_LIMITING"] = "true"

    # Reset rack-attack to clear any existing throttles
    Rack::Attack.reset! if Rack::Attack.respond_to?(:reset!)

    # Reload rack-attack configuration to pick up ENV changes
    load Rails.root.join("config/initializers/rack_attack.rb")

    # Ensure rack-attack uses the correct cache store
    Rack::Attack.cache.store = Rails.cache

    # Create a simple app for testing
    @app = ->(env) { [ 200, { "Content-Type" => "text/plain" }, [ "OK" ] ] }
    @middleware = Rack::Attack.new(@app)
  end

  def teardown
    Rails.cache.clear if Rails.cache.respond_to?(:clear)
    ENV.delete("ENABLE_RATE_LIMITING")
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "allows requests under rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/health")
    env["REMOTE_ADDR"] = "192.168.1.1"

    status, headers, _body = @middleware.call(env)

    assert_equal 200, status
    # rack-attack doesn't add headers by default, but we can check it didn't throttle
    assert_not_equal 429, status
  end

  test "blocks requests exceeding authentication rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    env["REMOTE_ADDR"] = "192.168.1.2"

    # Make requests up to the limit (5 requests allowed)
    5.times do |i|
      status, _headers, _body = @middleware.call(env.dup)
      assert_equal 200, status, "Request #{i+1} should succeed"
    end

    # 6th request should be blocked (limit is 5)
    status, headers, body = @middleware.call(env.dup)

    assert_equal 429, status, "6th request should be rate limited"
    assert_equal "0", headers["X-RateLimit-Remaining"], "Remaining should be 0"
    assert_equal "5", headers["X-RateLimit-Limit"], "Limit should be 5"

    response_body = JSON.parse(body.first)
    assert_equal "RATE_LIMIT_EXCEEDED", response_body["error"]["code"]
  end

  test "blocks requests exceeding AI processing rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
    env["REMOTE_ADDR"] = "192.168.1.3"

    # Make requests up to the limit
    10.times do
      _status, _headers, _body = @middleware.call(env.dup)
    end

    # Next request should be blocked
    status, _headers, _body = @middleware.call(env.dup)

    assert_equal 429, status
  end

  test "blocks requests exceeding file upload rate limit" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/primary_image", method: "POST",
                                    "CONTENT_TYPE" => "multipart/form-data")
    env["REMOTE_ADDR"] = "192.168.1.4"

    # Make requests up to the limit
    20.times do
      _status, _headers, _body = @middleware.call(env.dup)
    end

    # Next request should be blocked
    status, _headers, _body = @middleware.call(env.dup)

    assert_equal 429, status
  end

  test "uses standard rate limit for CRUD endpoints" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    env["REMOTE_ADDR"] = "192.168.1.5"

    status, _headers, _body = @middleware.call(env)

    assert_equal 200, status
  end

  test "identifies user by JWT token when available" do
    user = create(:user)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer #{token}")

    # Test the identifier extraction method directly
    request = Rack::Request.new(env)
    identifier = Rack::Attack.identifier_for(request)

    # Should extract user ID from token
    assert_match(/^user:\d+$/, identifier, "Should identify user from JWT token")
  end

  test "falls back to IP address when no token" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    request = Rack::Request.new(env)
    identifier = Rack::Attack.identifier_for(request)

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

    # Reload rack-attack to pick up the change
    load Rails.root.join("config/initializers/rack_attack.rb")
    middleware = Rack::Attack.new(@app)

    env = Rack::MockRequest.env_for("/api/v1/health")
    status, _headers, _body = middleware.call(env)

    assert_equal 200, status
  ensure
    ENV["ENABLE_RATE_LIMITING"] = original_value if original_value
    load Rails.root.join("config/initializers/rack_attack.rb")
  end

  test "skips rate limiting when DISABLE_RATE_LIMITING is set" do
    original_value = ENV["DISABLE_RATE_LIMITING"]
    ENV["DISABLE_RATE_LIMITING"] = "true"

    # Reload rack-attack to pick up the change
    load Rails.root.join("config/initializers/rack_attack.rb")
    middleware = Rack::Attack.new(@app)

    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    status, _headers, _body = middleware.call(env)

    assert_equal 200, status
  ensure
    ENV["DISABLE_RATE_LIMITING"] = original_value if original_value
    load Rails.root.join("config/initializers/rack_attack.rb")
  end

  test "handles invalid JWT token gracefully" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer invalid_token")
    request = Rack::Request.new(env)
    identifier = Rack::Attack.identifier_for(request)

    # Should fall back to IP when token is invalid
    assert_match(/^ip:/, identifier)
  end

  test "handles expired JWT token gracefully" do
    # Create an expired token
    expired_token = Auth::JsonWebToken.encode_access_token(user_id: 1, exp: 1.hour.ago.to_i)

    env = Rack::MockRequest.env_for("/api/v1/inventory_items",
                                    "HTTP_AUTHORIZATION" => "Bearer #{expired_token}")

    # Stub the decode to raise an exception (simulating expired token)
    Auth::JsonWebToken.stubs(:decode).raises(JWT::ExpiredSignature.new("Token expired"))

    request = Rack::Request.new(env)
    identifier = Rack::Attack.identifier_for(request)

    # Should fall back to IP when token is expired
    assert_match(/^ip:/, identifier)
  ensure
    Auth::JsonWebToken.unstub(:decode) if Auth::JsonWebToken.respond_to?(:unstub)
  end

  test "handles missing remote_ip by using unknown" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items")
    # Remove REMOTE_ADDR to simulate missing IP
    env.delete("REMOTE_ADDR")
    request = Rack::Request.new(env)
    identifier = Rack::Attack.identifier_for(request)

    assert_equal "ip:unknown", identifier
  end

  test "rate limits authentication endpoints correctly" do
    env = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    env["REMOTE_ADDR"] = "192.168.1.10"

    # Make 5 requests (the limit)
    5.times do
      status, _headers, _body = @middleware.call(env.dup)
      assert_equal 200, status, "Request should succeed before limit"
    end

    # 6th request should be blocked
    status, _headers, _body = @middleware.call(env.dup)
    assert_equal 429, status, "6th request should be blocked"
  end

  test "rate limits AI processing endpoints correctly" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/analyze_image_for_creation", method: "POST")
    env["REMOTE_ADDR"] = "192.168.1.11"

    # Make 10 requests (the limit)
    10.times do
      status, _headers, _body = @middleware.call(env.dup)
      assert_equal 200, status, "Request should succeed before limit"
    end

    # 11th request should be blocked
    status, _headers, _body = @middleware.call(env.dup)
    assert_equal 429, status, "11th request should be blocked"
  end

  test "rate limits file upload endpoints correctly" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items/1/primary_image", method: "POST",
                                    "CONTENT_TYPE" => "multipart/form-data")
    env["REMOTE_ADDR"] = "192.168.1.12"

    # Make 20 requests (the limit)
    20.times do
      status, _headers, _body = @middleware.call(env.dup)
      assert_equal 200, status, "Request should succeed before limit"
    end

    # 21st request should be blocked
    status, _headers, _body = @middleware.call(env.dup)
    assert_equal 429, status, "21st request should be blocked"
  end

  test "rate limits standard API endpoints correctly" do
    env = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET")
    env["REMOTE_ADDR"] = "192.168.1.13"

    # Make 100 requests (the limit)
    100.times do
      status, _headers, _body = @middleware.call(env.dup)
      assert_equal 200, status, "Request should succeed before limit"
    end

    # 101st request should be blocked
    status, _headers, _body = @middleware.call(env.dup)
    assert_equal 429, status, "101st request should be blocked"
  end

  test "different IPs have separate rate limits" do
    env1 = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    env1["REMOTE_ADDR"] = "192.168.1.20"

    env2 = Rack::MockRequest.env_for("/api/v1/auth/login", method: "POST")
    env2["REMOTE_ADDR"] = "192.168.1.21"

    # Exceed limit for IP1
    5.times { @middleware.call(env1.dup) }

    # IP2 should still be able to make requests
    status, _headers, _body = @middleware.call(env2.dup)
    assert_equal 200, status, "Different IP should have separate rate limit"

    # IP1 should be blocked
    status, _headers, _body = @middleware.call(env1.dup)
    assert_equal 429, status, "IP1 should be rate limited"
  end

  test "user-based rate limiting works with JWT token" do
    user1 = create(:user)
    user2 = create(:user)
    token1 = Auth::JsonWebToken.encode_access_token(user_id: user1.id)
    token2 = Auth::JsonWebToken.encode_access_token(user_id: user2.id)

    env1 = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET",
                                     "HTTP_AUTHORIZATION" => "Bearer #{token1}")
    env2 = Rack::MockRequest.env_for("/api/v1/inventory_items", method: "GET",
                                     "HTTP_AUTHORIZATION" => "Bearer #{token2}")

    # Exceed limit for user1
    100.times { @middleware.call(env1.dup) }

    # user2 should still be able to make requests
    status, _headers, _body = @middleware.call(env2.dup)
    assert_equal 200, status, "Different user should have separate rate limit"

    # user1 should be blocked
    status, _headers, _body = @middleware.call(env1.dup)
    assert_equal 429, status, "user1 should be rate limited"
  end
end
