#!/usr/bin/env ruby
# frozen_string_literal: true

# Quick verification script to check if Sidekiq setup is correct
require_relative "../config/environment"

puts "Verifying Sidekiq setup..."
puts "=" * 50

# Check Redis connection
begin
  if defined?(Sidekiq)
    Sidekiq.redis { |conn| conn.ping }
    puts "✓ Redis connection via Sidekiq: OK"
  else
    require "redis"
    redis = Redis.new(url: ENV.fetch("REDIS_URL", "redis://127.0.0.1:6379/0"))
    redis.ping
    redis.close
    puts "✓ Redis connection: OK"
  end
rescue => e
  puts "✗ Redis connection failed: #{e.message}"
  exit 1
end

# Check Sidekiq configuration
if defined?(Sidekiq)
  puts "✓ Sidekiq gem loaded"
  puts "  Redis URL: #{Sidekiq.redis { |c| c.connection[:location] } rescue ENV.fetch('REDIS_URL', 'redis://127.0.0.1:6379/0')}"
else
  puts "✗ Sidekiq gem not loaded"
  exit 1
end

# Check Active Job adapter
adapter = Rails.application.config.active_job.queue_adapter
puts "✓ Active Job adapter: #{adapter}"

if adapter == :sidekiq
  puts "✓ Active Job is configured to use Sidekiq"
else
  puts "⚠ Active Job adapter is #{adapter}, not :sidekiq"
end

puts "=" * 50
puts "Setup looks good! You can run 'bin/dev' now."
puts "Sidekiq will start automatically via Procfile.dev"

