# frozen_string_literal: true

# Redis configuration for caching and vector storage
# Default URL: redis://127.0.0.1:6379/0

redis_url = ENV.fetch("REDIS_URL", "redis://127.0.0.1:6379/0")

# Configure Redis connection
Rails.application.configure do
  # Configure Redis for caching
  config.cache_store = :redis_cache_store, {
    url: redis_url,
    namespace: "sastaspace:cache:#{Rails.env}",
    expires_in: 1.hour
  }

  # Configure ActiveJob to use async adapter for now (Redis adapter needs additional gem)
  config.active_job.queue_adapter = :async
end

# Global Redis instance for custom operations (vector storage, etc.)
$redis = Redis.new(url: redis_url)

# Health check helper for Redis connectivity
module RedisHealthCheck
  def self.healthy?
    $redis.ping == "PONG"
  rescue Redis::BaseError, Errno::ECONNREFUSED, Errno::EHOSTUNREACH
    false
  end

  def self.info
    return { status: "unhealthy", error: "Connection failed" } unless healthy?
    
    $redis.info.slice("redis_version", "used_memory_human", "connected_clients")
  rescue Redis::BaseError, Errno::ECONNREFUSED, Errno::EHOSTUNREACH => e
    { status: "unhealthy", error: e.message }
  end
end
