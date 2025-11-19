require "test_helper"

class SecurityHeadersMiddlewareTest < ActiveSupport::TestCase
  test "adds security headers to response" do
    app = ->(env) { [ 200, {}, [ "OK" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    status, headers, response = middleware.call({})

    assert_equal "DENY", headers["X-Frame-Options"]
    assert_equal "nosniff", headers["X-Content-Type-Options"]
    assert_equal "1; mode=block", headers["X-XSS-Protection"]
    assert_equal "strict-origin-when-cross-origin", headers["Referrer-Policy"]
    assert headers["Content-Security-Policy"].present?
    assert headers["Permissions-Policy"].present?
  end

  test "adds HSTS header in production with HTTPS" do
    app = ->(env) { [ 200, {}, [ "OK" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    Rails.stubs(:env).returns(ActiveSupport::StringInquirer.new("production"))

    status, headers, response = middleware.call({ "rack.url_scheme" => "https" })

    assert headers["Strict-Transport-Security"].present?
  end

  test "does not add HSTS header in non-production" do
    app = ->(env) { [ 200, {}, [ "OK" ] ] }
    middleware = SecurityHeadersMiddleware.new(app)

    Rails.stubs(:env).returns(ActiveSupport::StringInquirer.new("development"))

    status, headers, response = middleware.call({ "rack.url_scheme" => "https" })

    assert_nil headers["Strict-Transport-Security"]
  end
end
