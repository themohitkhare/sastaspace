# Rate limiting interface for API endpoints
# Provides a local stub for rate limiting (can be replaced with Redis-based implementation)
module RateLimiting
  extend ActiveSupport::Concern

  included do
    # Rate limit by default (can be overridden per controller)
    before_action :check_rate_limit, if: :rate_limiting_enabled?
  end

  class_methods do
    # Configure rate limiting for specific actions
    # @param options [Hash] Rate limit options
    # @option options [Integer] :limit Number of requests allowed
    # @option options [Integer] :period Time period in seconds
    # @option options [Symbol] :key_method Method to call for rate limit key (default: :current_user)
    def rate_limit(options = {})
      @rate_limit_options = {
        limit: options[:limit] || 100,
        period: options[:period] || 60,
        key_method: options[:key_method] || :current_user
      }
    end

    def rate_limit_options
      @rate_limit_options || { limit: 100, period: 60, key_method: :current_user }
    end
  end

  private

  def rate_limiting_enabled?
    # Enable rate limiting in production and staging
    # Can be disabled in development/test via env var
    return false if Rails.env.test?
    return false if ENV["DISABLE_RATE_LIMITING"] == "true"
    true
  end

  def check_rate_limit
    options = self.class.rate_limit_options
    key = rate_limit_key(options[:key_method])

    return unless key.present?

    # Check current rate limit (local stub implementation)
    # In production, this would use Redis or similar
    current_count = get_rate_limit_count(key, options[:period])

    if current_count >= options[:limit]
      log_warn("Rate limit exceeded", {
        key: key,
        limit: options[:limit],
        period: options[:period]
      })

      render_error_response(
        code: "RATE_LIMIT_EXCEEDED",
        message: "Rate limit exceeded. Please try again later.",
        details: {
          limit: options[:limit],
          period: options[:period],
          retry_after: options[:period]
        },
        status: :too_many_requests
      )
      return
    end

    # Increment rate limit counter
    increment_rate_limit(key, options[:period])
  end

  def rate_limit_key(key_method)
    if respond_to?(key_method, true)
      user = send(key_method)
      return "api:#{user&.id || request.remote_ip}"
    end
    "api:#{request.remote_ip}"
  end

  # Local stub implementation - uses Rails cache
  # In production, replace with Redis-based implementation
  def get_rate_limit_count(key, period)
    cache_key = "rate_limit:#{key}:#{period}"
    Rails.cache.read(cache_key) || 0
  end

  def increment_rate_limit(key, period)
    cache_key = "rate_limit:#{key}:#{period}"
    current_count = Rails.cache.read(cache_key) || 0
    Rails.cache.write(cache_key, current_count + 1, expires_in: period.seconds)
  end
end
