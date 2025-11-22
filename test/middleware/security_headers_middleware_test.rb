require "test_helper"

class SecurityHeadersMiddlewareTest < ActiveSupport::TestCase
  setup do
    @app = ->(env) { [ 200, {}, [ "OK" ] ] }
    @middleware = SecurityHeadersMiddleware.new(@app)
  end

  test "adds security headers to response" do
    env = Rack::MockRequest.env_for("http://example.com")
    status, headers, body = @middleware.call(env)

    assert_equal 200, status
    assert_equal "nosniff", headers["X-Content-Type-Options"]
    assert_equal "DENY", headers["X-Frame-Options"]
    assert_equal "1; mode=block", headers["X-XSS-Protection"]
    assert_equal "strict-origin-when-cross-origin", headers["Referrer-Policy"]
    assert_includes headers["Permissions-Policy"], "geolocation=()"
    assert_includes headers["Permissions-Policy"], "camera=()"
  end

  test "sets Content-Security-Policy header" do
    env = Rack::MockRequest.env_for("http://example.com")
    _, headers, _ = @middleware.call(env)

    csp = headers["Content-Security-Policy"]
    assert_not_nil csp
    assert_includes csp, "default-src 'self'"
    assert_includes csp, "script-src 'self'"
    assert_includes csp, "style-src 'self'"
    assert_includes csp, "img-src 'self' data: https:"
    assert_includes csp, "font-src 'self' data:"
    assert_includes csp, "connect-src 'self'"
  end

  test "allows unsafe-inline for scripts and styles in development" do
    original_env = Rails.env
    begin
      Rails.env = "development"
      @middleware = SecurityHeadersMiddleware.new(@app)

      env = Rack::MockRequest.env_for("http://example.com")
      _, headers, _ = @middleware.call(env)

      csp = headers["Content-Security-Policy"]
      assert_includes csp, "'unsafe-inline'"
      assert_includes csp, "'unsafe-eval'"
    ensure
      Rails.env = original_env
    end
  end

  test "does not modify response body" do
    env = Rack::MockRequest.env_for("http://example.com")
    _, _, body = @middleware.call(env)

    assert_equal [ "OK" ], body
  end

  test "preserves existing headers from app" do
    app_with_headers = ->(env) { [ 200, { "X-Custom-Header" => "custom" }, [ "OK" ] ] }
    middleware = SecurityHeadersMiddleware.new(app_with_headers)

    env = Rack::MockRequest.env_for("http://example.com")
    _, headers, _ = middleware.call(env)

    assert_equal "custom", headers["X-Custom-Header"]
    assert_equal "nosniff", headers["X-Content-Type-Options"]
  end

  test "handles different HTTP methods" do
    %w[GET POST PUT PATCH DELETE].each do |method|
      env = Rack::MockRequest.env_for("http://example.com", method: method)
      status, headers, _ = @middleware.call(env)

      assert_equal 200, status
      assert_equal "nosniff", headers["X-Content-Type-Options"], "Should add headers for #{method}"
    end
  end

  test "adds headers for error responses" do
    error_app = ->(env) { [ 500, {}, [ "Error" ] ] }
    middleware = SecurityHeadersMiddleware.new(error_app)

    env = Rack::MockRequest.env_for("http://example.com")
    status, headers, _ = middleware.call(env)

    assert_equal 500, status
    assert_equal "nosniff", headers["X-Content-Type-Options"]
  end

  test "adds HSTS header in production with HTTPS" do
    original_env = Rails.env
    begin
      Rails.env = "production"
      middleware = SecurityHeadersMiddleware.new(@app)

      # HTTPS request
      env = Rack::MockRequest.env_for("https://example.com")
      env["rack.url_scheme"] = "https"
      _, headers, _ = middleware.call(env)

      assert_not_nil headers["Strict-Transport-Security"]
      assert_includes headers["Strict-Transport-Security"], "max-age=31536000"
      assert_includes headers["Strict-Transport-Security"], "includeSubDomains"
      assert_includes headers["Strict-Transport-Security"], "preload"
    ensure
      Rails.env = original_env
    end
  end

  test "does not add HSTS header in production with HTTP" do
    original_env = Rails.env
    begin
      Rails.env = "production"
      middleware = SecurityHeadersMiddleware.new(@app)

      # HTTP request (not HTTPS)
      env = Rack::MockRequest.env_for("http://example.com")
      env["rack.url_scheme"] = "http"
      _, headers, _ = middleware.call(env)

      assert_nil headers["Strict-Transport-Security"]
    ensure
      Rails.env = original_env
    end
  end

  test "does not add HSTS header in non-production environments" do
    original_env = Rails.env
    begin
      Rails.env = "development"
      middleware = SecurityHeadersMiddleware.new(@app)

      # HTTPS request but in development
      env = Rack::MockRequest.env_for("https://example.com")
      env["rack.url_scheme"] = "https"
      _, headers, _ = middleware.call(env)

      assert_nil headers["Strict-Transport-Security"]
    ensure
      Rails.env = original_env
    end
  end
end
