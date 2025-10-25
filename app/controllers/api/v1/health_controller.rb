module Api
  module V1
    class HealthController < ApplicationController
      include StructuredLogging

      def show
        health_status = check_health
        status = health_status[:healthy] ? :ok : :service_unavailable
        
        log_info("Health check performed", { 
          healthy: health_status[:healthy],
          checks: health_status[:checks].keys 
        })
        
        render json: {
          status: health_status[:healthy] ? "healthy" : "unhealthy",
          timestamp: Time.current.iso8601,
          checks: health_status[:checks]
        }, status: status
      end

      private

      def check_health
        checks = {
          database: check_database,
          cache: check_cache,
          queue: check_queue,
          storage: check_storage,
          ollama: check_ollama
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

      def check_storage
        # Check if Active Storage is accessible
        start_time = Time.current
        ActiveStorage::Blob.count
        duration = ((Time.current - start_time) * 1000).round(2)
        
        { status: "ok", duration_ms: duration }
      rescue => e
        { status: "error", error: e.message }
      end

      def check_ollama
        # Stubbed check for Ollama service
        # In tests, this will be mocked
        { status: "ok", note: "stubbed in tests" }
      end
    end
  end
end
