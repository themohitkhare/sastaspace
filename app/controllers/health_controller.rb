class HealthController < ApplicationController
  def show
    health_status = check_health
    status = health_status[:healthy] ? :ok : :service_unavailable
    
    render json: {
      status: health_status[:healthy] ? "ok" : "error",
      timestamp: Time.current.iso8601,
      checks: health_status[:checks]
    }, status: status
  end

  private

  def check_health
    checks = {
      database: check_database,
      cache: check_cache,
      queue: check_queue
    }

    healthy = checks.values.all? { |check| check[:status] == "ok" }

    { healthy: healthy, checks: checks }
  end

  def check_database
    start_time = Time.current
    ActiveRecord::Base.connection.execute("SELECT 1")
    duration = ((Time.current - start_time) * 1000).round(2)
    
    { status: "ok", duration_ms: duration }
  rescue => e
    { status: "error", error: e.message }
  end

  def check_cache
    start_time = Time.current
    Rails.cache.write("health_check", "ok", expires_in: 1.second)
    Rails.cache.read("health_check")
    duration = ((Time.current - start_time) * 1000).round(2)
    
    { status: "ok", duration_ms: duration }
  rescue => e
    { status: "error", error: e.message }
  end

  def check_queue
    # Check if Solid Queue is accessible
    start_time = Time.current
    SolidQueue::Job.count
    duration = ((Time.current - start_time) * 1000).round(2)
    
    { status: "ok", duration_ms: duration }
  rescue => e
    { status: "error", error: e.message }
  end
end
