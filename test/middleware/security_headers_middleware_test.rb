require "test_helper"

class SecurityHeadersMiddlewareTest < ActiveSupport::TestCase
  def setup
    @app = ->(env) { [ 200, {}, [ "OK" ] ] }
    @middleware = SecurityHeadersMiddleware.new(@app)
  end

  test "adds X-Frame-Options header" do
    status, headers, _body = @middleware.call({})
    assert_equal "DENY", headers["X-Frame-Options"]
  end

  test "adds X-Content-Type-Options header" do
    status, headers, _body = @middleware.call({})
    assert_equal "nosniff", headers["X-Content-Type-Options"]
  end

  test "adds X-XSS-Protection header" do
    status, headers, _body = @middleware.call({})
    assert_equal "1; mode=block", headers["X-XSS-Protection"]
  end

  test "adds Referrer-Policy header" do
    status, headers, _body = @middleware.call({})
    assert_equal "strict-origin-when-cross-origin", headers["Referrer-Policy"]
  end

  test "adds Content-Security-Policy header" do
    status, headers, _body = @middleware.call({})
    csp = headers["Content-Security-Policy"]
    assert csp.present?
    assert_includes csp, "default-src 'self'"
    assert_includes csp, "script-src 'self'"
    assert_includes csp, "style-src 'self'"
    assert_includes csp, "img-src 'self' data: https:"
  end

  test "adds Permissions-Policy header" do
    status, headers, _body = @middleware.call({})
    assert_equal "geolocation=(), microphone=(), camera=()", headers["Permissions-Policy"]
  end

  test "adds HSTS header in production with HTTPS" do
    Rails.env.stubs(:production?).returns(true)
    env = { "rack.url_scheme" => "https" }
    status, headers, _body = @middleware.call(env)
    assert headers["Strict-Transport-Security"].present?
    assert_includes headers["Strict-Transport-Security"], "max-age=31536000"
  end

  test "does not add HSTS header in production without HTTPS" do
    Rails.env.stubs(:production?).returns(true)
    env = { "rack.url_scheme" => "http" }
    status, headers, _body = @middleware.call(env)
    assert_nil headers["Strict-Transport-Security"]
  end

  test "does not add HSTS header in non-production" do
    Rails.env.stubs(:production?).returns(false)
    env = { "rack.url_scheme" => "https" }
    status, headers, _body = @middleware.call(env)
    assert_nil headers["Strict-Transport-Security"]
  end

  test "preserves original response status" do
    app = ->(env) { [ 404, {}, [ "Not Found" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)
    status, _headers, _body = middleware.call({})
    assert_equal 404, status
  end

  test "preserves original response body" do
    app = ->(env) { [ 200, {}, [ "Custom Body" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)
    _status, _headers, body = middleware.call({})
    assert_equal [ "Custom Body" ], body
  end

  test "CSP policy includes all required directives" do
    status, headers, _body = @middleware.call({})
    csp = headers["Content-Security-Policy"]

    assert_includes csp, "default-src 'self'"
    assert_includes csp, "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    assert_includes csp, "style-src 'self' 'unsafe-inline'"
    assert_includes csp, "img-src 'self' data: https:"
    assert_includes csp, "font-src 'self' data:"
    assert_includes csp, "connect-src 'self'"
    assert_includes csp, "frame-ancestors 'none'"
    assert_includes csp, "base-uri 'self'"
    assert_includes csp, "form-action 'self'"
  end

  test "CSP policy uses semicolon separators" do
    status, headers, _body = @middleware.call({})
    csp = headers["Content-Security-Policy"]

    # Should have semicolons between directives
    assert_match(/;/, csp)
    # Should not have double semicolons
    refute_match(/;;/, csp)
  end
end
