# Rate limiting middleware for API endpoints
# Provides configurable rate limiting with different limits per endpoint type
class RateLimitingMiddleware
  # Rate limit configurations by endpoint type
  RATE_LIMITS = {
    authentication: { limit: 5, period: 60 },      # 5 attempts per minute
    ai_processing: { limit: 10, period: 3600 },    # 10 requests per hour
    file_upload: { limit: 20, period: 3600 },      # 20 requests per hour
    standard: { limit: 100, period: 60 }            # 100 requests per minute (default)
  }.freeze

  def initialize(app)
    @app = app
  end

  def call(env)
    request = ActionDispatch::Request.new(env)

    # Skip rate limiting for non-API requests
    return @app.call(env) unless api_request?(request)

    # Skip rate limiting in test environment unless explicitly enabled
    # Note: Tests can enable it by setting ENABLE_RATE_LIMITING=true
    return @app.call(env) if Rails.env.test? && ENV["ENABLE_RATE_LIMITING"] != "true"

    # Skip if rate limiting is disabled
    return @app.call(env) if ENV["DISABLE_RATE_LIMITING"] == "true"

    # Determine endpoint type and rate limit configuration
    endpoint_type = determine_endpoint_type(request)
    config = RATE_LIMITS[endpoint_type] || RATE_LIMITS[:standard]

    # Get identifier (user ID or IP address)
    identifier = get_identifier(request)

    # Check rate limit
    if rate_limit_exceeded?(identifier, endpoint_type, config)
      return rate_limit_response(config)
    end

    # Increment counter before processing request
    cache_key = "rate_limit:#{endpoint_type}:#{identifier}:#{config[:period]}"
    current_count = Rails.cache.read(cache_key) || 0
    Rails.cache.write(cache_key, current_count + 1, expires_in: config[:period].seconds)

    # Process request and add rate limit headers
    status, headers, response = @app.call(env)

    # Add rate limit headers to response
    add_rate_limit_headers(headers, identifier, endpoint_type, config)

    [ status, headers, response ]
  end

  private

  def api_request?(request)
    request.path.start_with?("/api/")
  end

  def determine_endpoint_type(request)
    path = request.path

    # Authentication endpoints
    if path.match?(%r{/api/v1/auth/(login|register)})
      return :authentication
    end

    # AI processing endpoints
    if path.match?(%r{/api/v1/(inventory_items|outfits|ai).*analyze}) ||
       path.match?(%r{/api/v1/ai/})
      return :ai_processing
    end

    # File upload endpoints
    if path.match?(%r{/api/v1/.*/(primary_image|additional_images|analyze_photo|analyze_image_for_creation)}) ||
       request.post? && request.content_type&.start_with?("multipart/form-data")
      return :file_upload
    end

    # Default to standard CRUD
    :standard
  end

  def get_identifier(request)
    # Try to get user ID from JWT token if available
    auth_header = request.headers["Authorization"]
    if auth_header&.start_with?("Bearer ")
      token = auth_header.sub("Bearer ", "")
      begin
        decoded = Auth::JsonWebToken.decode(token)
        return "user:#{decoded[:user_id]}" if decoded[:user_id]
      rescue StandardError
        # If token is invalid or expired, fall back to IP
      end
    end

    # Fall back to IP address (use "unknown" if IP is not available)
    ip = request.remote_ip.presence || "unknown"
    "ip:#{ip}"
  end

  def rate_limit_exceeded?(identifier, endpoint_type, config)
    cache_key = "rate_limit:#{endpoint_type}:#{identifier}:#{config[:period]}"
    current_count = Rails.cache.read(cache_key) || 0

    # Check if limit would be exceeded after increment
    if current_count >= config[:limit]
      # Log rate limit violation
      Rails.logger.warn("Rate limit exceeded: identifier=#{identifier}, endpoint_type=#{endpoint_type}, limit=#{config[:limit]}, period=#{config[:period]}")
      return true
    end

    false
  end

  def rate_limit_response(config)
    headers = {
      "Content-Type" => "application/json",
      "X-RateLimit-Limit" => config[:limit].to_s,
      "X-RateLimit-Remaining" => "0",
      "X-RateLimit-Reset" => (Time.now + config[:period].seconds).to_i.to_s,
      "Retry-After" => config[:period].to_s
    }

    body = {
      success: false,
      error: {
        code: "RATE_LIMIT_EXCEEDED",
        message: "Rate limit exceeded. Please try again later.",
        details: {
          limit: config[:limit],
          period: config[:period],
          retry_after: config[:period]
        }
      },
      timestamp: Time.current.iso8601
    }.to_json

    [ 429, headers, [ body ] ]
  end

  def add_rate_limit_headers(headers, identifier, endpoint_type, config)
    cache_key = "rate_limit:#{endpoint_type}:#{identifier}:#{config[:period]}"
    current_count = Rails.cache.read(cache_key) || 0
    remaining = [ config[:limit] - current_count, 0 ].max

    headers["X-RateLimit-Limit"] = config[:limit].to_s
    headers["X-RateLimit-Remaining"] = remaining.to_s
    headers["X-RateLimit-Reset"] = (Time.now + config[:period].seconds).to_i.to_s
  end
end
