require "test_helper"

class SecurityHeadersMiddlewareTest < ActiveSupport::TestCase
  def setup
    @app = ->(env) { [ 200, {}, [ "OK" ] ] }
    @middleware = SecurityHeadersMiddleware.new(@app)
  end

  test "adds X-Frame-Options header" do
    status, headers, _response = @middleware.call({})

    assert_equal "DENY", headers["X-Frame-Options"]
  end

  test "adds X-Content-Type-Options header" do
    status, headers, _response = @middleware.call({})

    assert_equal "nosniff", headers["X-Content-Type-Options"]
  end

  test "adds X-XSS-Protection header" do
    status, headers, _response = @middleware.call({})

    assert_equal "1; mode=block", headers["X-XSS-Protection"]
  end

  test "adds Referrer-Policy header" do
    status, headers, _response = @middleware.call({})

    assert_equal "strict-origin-when-cross-origin", headers["Referrer-Policy"]
  end

  test "adds Content-Security-Policy header" do
    status, headers, _response = @middleware.call({})

    assert headers["Content-Security-Policy"].present?
    assert_match(/default-src 'self'/, headers["Content-Security-Policy"])
    assert_match(/script-src/, headers["Content-Security-Policy"])
    assert_match(/style-src/, headers["Content-Security-Policy"])
    assert_match(/img-src/, headers["Content-Security-Policy"])
  end

  test "adds Permissions-Policy header" do
    status, headers, _response = @middleware.call({})

    assert_equal "geolocation=(), microphone=(), camera=()", headers["Permissions-Policy"]
  end

  test "adds Strict-Transport-Security in production with HTTPS" do
    original_env = Rails.env
    Rails.env = ActiveSupport::StringInquirer.new("production")

    env = { "rack.url_scheme" => "https" }
    status, headers, _response = @middleware.call(env)

    assert_equal "max-age=31536000; includeSubDomains; preload", headers["Strict-Transport-Security"]
  ensure
    Rails.env = original_env
  end

  test "does not add Strict-Transport-Security in development" do
    original_env = Rails.env
    Rails.env = ActiveSupport::StringInquirer.new("development")

    env = { "rack.url_scheme" => "https" }
    status, headers, _response = @middleware.call(env)

    assert_nil headers["Strict-Transport-Security"]
  ensure
    Rails.env = original_env
  end

  test "does not add Strict-Transport-Security for HTTP" do
    original_env = Rails.env
    Rails.env = ActiveSupport::StringInquirer.new("production")

    env = { "rack.url_scheme" => "http" }
    status, headers, _response = @middleware.call(env)

    assert_nil headers["Strict-Transport-Security"]
  ensure
    Rails.env = original_env
  end

  test "preserves original response status" do
    app = ->(env) { [ 404, {}, [ "Not Found" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    status, _headers, _response = middleware.call({})

    assert_equal 404, status
  end

  test "preserves original response body" do
    app = ->(env) { [ 200, {}, [ "Custom Response" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    _status, _headers, response = middleware.call({})

    assert_equal [ "Custom Response" ], response
  end

  test "preserves existing headers from app" do
    app = ->(env) { [ 200, { "Custom-Header" => "value" }, [ "OK" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    _status, headers, _response = middleware.call({})

    assert_equal "value", headers["Custom-Header"]
    assert_equal "DENY", headers["X-Frame-Options"] # Security headers still added
  end
end
