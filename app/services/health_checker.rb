# frozen_string_literal: true

class HealthChecker
  def self.check_all
    {
      status: overall_status,
      timestamp: Time.current.iso8601,
      services: {
        database: database_status,
        cache: cache_status,
        jobs: jobs_status
      }
    }
  end

  def self.overall_status
    return "healthy" if all_services_healthy?
    "unhealthy"
  end

  def self.database_status
    ActiveRecord::Base.connection.execute("SELECT 1")
    { status: "healthy", message: "Database connection successful" }
  rescue StandardError => e
    { status: "unhealthy", error: e.message }
  end

  def self.cache_status
    Rails.cache.write("health_check", "ok", expires_in: 1.minute)
    cached_value = Rails.cache.read("health_check")

    if cached_value == "ok"
      { status: "healthy", message: "Cache store operational" }
    else
      { status: "unhealthy", error: "Cache read/write failed" }
    end
  rescue StandardError => e
    { status: "unhealthy", error: e.message }
  end

  def self.jobs_status
    # Get comprehensive job queue health from monitoring service
    health = JobMonitoringService.queue_health

    {
      status: health[:status] == "healthy" ? "healthy" : "unhealthy",
      message: "Job queue operational",
      queue_depth: health[:queues].values.sum { |q| q[:depth] },
      workers: health[:workers][:active],
      alerts: health[:alerts].count
    }
  rescue StandardError => e
    { status: "unhealthy", error: e.message }
  end

  private

  def self.all_services_healthy?
    [ database_status, cache_status, jobs_status ].all? do |service|
      service[:status] == "healthy"
    end
  end

  # Simple test job for health checking
  class TestHealthJob < ApplicationJob
    def perform(message)
      Rails.logger.info "Health check job executed: #{message}"
    end
  end
end
