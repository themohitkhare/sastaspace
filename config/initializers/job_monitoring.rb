# Job monitoring configuration and initialization
# Sets up monitoring for background jobs and provides health check integration

Rails.application.config.after_initialize do
  # Log job monitoring configuration on startup
  Rails.logger.info "[JobMonitoring] Initializing job monitoring service"

  # Verify Solid Queue is available
  if defined?(SolidQueue)
    Rails.logger.info "[JobMonitoring] ✓ Solid Queue detected"
  else
    Rails.logger.warn "[JobMonitoring] ⚠ Solid Queue not detected - monitoring may be limited"
  end

  # Log initial queue health (if not in test environment)
  unless Rails.env.test?
    begin
      health = JobMonitoringService.queue_health
      Rails.logger.info "[JobMonitoring] Initial queue health: #{health[:status]}"
      Rails.logger.info "[JobMonitoring] Active workers: #{health[:workers][:active]}"
      Rails.logger.info "[JobMonitoring] Queue depths: #{health[:queues].inspect}"

      if health[:alerts].any?
        Rails.logger.warn "[JobMonitoring] Active alerts: #{health[:alerts].count}"
        health[:alerts].each do |alert|
          Rails.logger.warn "[JobMonitoring] #{alert[:level].upcase}: #{alert[:message]}"
        end
      end
    rescue StandardError => e
      Rails.logger.error "[JobMonitoring] Error checking initial health: #{e.message}"
    end
  end
end

# Configure alert thresholds (can be overridden via environment variables)
# Note: These use default values that match JobMonitoringService constants
module JobMonitoringConfig
  QUEUE_DEPTH_WARNING = ENV.fetch("JOB_QUEUE_DEPTH_WARNING", 100).to_i
  QUEUE_DEPTH_CRITICAL = ENV.fetch("JOB_QUEUE_DEPTH_CRITICAL", 500).to_i
  FAILURE_RATE_WARNING = ENV.fetch("JOB_FAILURE_RATE_WARNING", 0.05).to_f
  FAILURE_RATE_CRITICAL = ENV.fetch("JOB_FAILURE_RATE_CRITICAL", 0.10).to_f
  STALE_JOB_WARNING = ENV.fetch("JOB_STALE_WARNING_SECONDS", 3600).seconds
  STALE_JOB_CRITICAL = ENV.fetch("JOB_STALE_CRITICAL_SECONDS", 14400).seconds
  WORKER_STALE_WARNING = ENV.fetch("JOB_WORKER_STALE_WARNING_SECONDS", 120).seconds
  WORKER_STALE_CRITICAL = ENV.fetch("JOB_WORKER_STALE_CRITICAL_SECONDS", 300).seconds
end
