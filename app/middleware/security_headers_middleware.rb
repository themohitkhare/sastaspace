# Security headers middleware
# Adds security headers to all responses for protection against common attacks
class SecurityHeadersMiddleware
  def initialize(app)
    @app = app
  end

  def call(env)
    status, headers, response = @app.call(env)

    # Add security headers
    headers["X-Frame-Options"] = "DENY"
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-XSS-Protection"] = "1; mode=block"
    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS (HTTP Strict Transport Security) - only in production with HTTPS
    if Rails.env.production? && env["rack.url_scheme"] == "https"
      headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    end

    # Content Security Policy
    # Allow self, data URIs for images, and inline styles/scripts for Rails UJS
    csp_policy = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'", # unsafe-eval needed for some JS frameworks
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'"
    ].join("; ")

    headers["Content-Security-Policy"] = csp_policy

    # Permissions Policy (formerly Feature Policy)
    headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    [ status, headers, response ]
  end
end
