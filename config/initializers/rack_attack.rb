# frozen_string_literal: true

# Rack::Attack configuration for rate limiting
# See https://github.com/rack/rack-attack for documentation

class Rack::Attack
  # Use Rails cache store for rate limiting
  self.cache.store = Rails.cache

  # Helper to extract user ID from JWT token
  # request is a Rack::Attack::Request which wraps Rack::Request
  def self.user_id_from_request(request)
    # Rack::Attack::Request provides access to headers via get_header or env
    auth_header = request.get_header("HTTP_AUTHORIZATION") || request.env["HTTP_AUTHORIZATION"]
    return nil unless auth_header&.start_with?("Bearer ")

    token = auth_header.sub("Bearer ", "")
    begin
      decoded = Auth::JsonWebToken.decode(token)
      decoded[:user_id]
    rescue StandardError
      nil
    end
  end

  # Helper to get identifier (user ID or IP)
  # request is a Rack::Attack::Request which wraps Rack::Request
  def self.identifier_for(request)
    user_id = user_id_from_request(request)
    return "user:#{user_id}" if user_id

    # Extract IP from env (Rack::Attack::Request wraps Rack::Request, access via env)
    ip = request.env["REMOTE_ADDR"] || request.env["HTTP_X_FORWARDED_FOR"]&.split(",")&.first&.strip || "unknown"
    "ip:#{ip}"
  end

  # Enable/disable rate limiting via environment variable
  # In test environment, enable with ENABLE_RATE_LIMITING=true
  # Disable globally with DISABLE_RATE_LIMITING=true
  unless (Rails.env.test? && ENV["ENABLE_RATE_LIMITING"] != "true") || ENV["DISABLE_RATE_LIMITING"] == "true"
    # IMPORTANT: More specific throttles must be defined BEFORE general ones
    # rack-attack evaluates throttles in order and uses the first matching one

    # Authentication endpoints: 5 requests per minute
    throttle("req/ip:auth", limit: 5, period: 60) do |req|
      if req.path.match?(%r{/api/v1/auth/(login|register)})
        identifier_for(req)
      end
    end

    # File upload endpoints: 20 requests per hour (check before AI processing)
    throttle("req/ip:file_upload", limit: 20, period: 3600) do |req|
      content_type = req.content_type || req.env["CONTENT_TYPE"]
      if req.path.match?(%r{/api/v1/.*/(primary_image|additional_images|analyze_photo|analyze_image_for_creation)}) ||
         (req.post? && content_type&.start_with?("multipart/form-data"))
        identifier_for(req)
      end
    end

    # AI processing endpoints: 10 requests per hour
    throttle("req/ip:ai_processing", limit: 10, period: 3600) do |req|
      if req.path.match?(%r{/api/v1/(inventory_items|outfits|ai).*analyze}) ||
         req.path.match?(%r{/api/v1/ai/})
        identifier_for(req)
      end
    end

    # Standard API endpoints: 100 requests per minute (most general, defined last)
    throttle("req/ip:api", limit: 100, period: 60) do |req|
      if req.path.start_with?("/api/")
        identifier_for(req)
      end
    end
  end

  # Custom response for rate limit exceeded
  self.throttled_responder = lambda do |request|
    # request is a Rack::Attack::Request, match_data is in request.env
    match_data = request.env["rack.attack.match_data"] || {}
    now = match_data[:epoch_time] || Time.now.to_i
    period = match_data[:period] || 60
    limit = match_data[:limit] || 100
    retry_after = period - (now % period)

    headers = {
      "Content-Type" => "application/json",
      "X-RateLimit-Limit" => limit.to_s,
      "X-RateLimit-Remaining" => "0",
      "X-RateLimit-Reset" => (now + retry_after).to_i.to_s,
      "Retry-After" => retry_after.to_s
    }

    body = {
      success: false,
      error: {
        code: "RATE_LIMIT_EXCEEDED",
        message: "Rate limit exceeded. Please try again later.",
        details: {
          limit: limit,
          period: period,
          retry_after: retry_after
        }
      },
      timestamp: Time.current.iso8601
    }.to_json

    [ 429, headers, [ body ] ]
  end

  # Log blocked requests
  ActiveSupport::Notifications.subscribe("rack.attack") do |_name, _start, _finish, _request_id, payload|
    req = payload[:request]
    if req.env["rack.attack.match_type"] == :throttle
      Rails.logger.warn("Rate limit exceeded: #{req.env['rack.attack.matched']} - #{req.ip}")
    end
  end
end
