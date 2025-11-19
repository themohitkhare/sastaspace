# Sidekiq configuration
# See https://github.com/sidekiq/sidekiq/wiki/Configuration for options
# Note: Sidekiq 7+ no longer supports Redis namespaces
# Use different Redis databases (0 for jobs, 1 for cache) instead

redis_url = ENV.fetch("REDIS_URL", "redis://127.0.0.1:6379/0")

Sidekiq.configure_server do |config|
  config.redis = {
    url: redis_url,
    size: ENV.fetch("SIDEKIQ_CONCURRENCY", 25).to_i + 5 # Connection pool size
  }

  # Note: Queue processing order is configured when starting Sidekiq
  # Default queues: ai_critical, default (ai_critical processed first)
  # To specify queues when starting Sidekiq:
  # bundle exec sidekiq -q ai_critical -q default
  # Or use bin/jobs which reads from Sidekiq.options[:queues]

  # Optional: Configure job retry, dead job queue, etc.
  # config.death_handlers << ->(job, ex) { ... }
end

Sidekiq.configure_client do |config|
  config.redis = {
    url: redis_url,
    size: 5 # Smaller pool for client
  }
end

# Sidekiq Web UI routes are handled by Mission Control Jobs
# Access via /admin/jobs/monitor (requires admin authentication)
