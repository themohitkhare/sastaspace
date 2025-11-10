# Concern for job-specific monitoring and metrics
# Provides hooks for tracking job performance and failures
module Monitorable
  extend ActiveSupport::Concern

  included do
    # Track job start time for performance monitoring
    around_perform :track_job_performance

    # Track job failures
    rescue_from StandardError, with: :track_job_failure
  end

  private

  def track_job_performance
    start_time = Time.current
    job_class = self.class.name

    Rails.logger.info "[JobMonitor] Starting #{job_class} (job_id: #{job_id})"

    yield

    duration_ms = ((Time.current - start_time) * 1000).round(2)
    Rails.logger.info "[JobMonitor] Completed #{job_class} in #{duration_ms}ms (job_id: #{job_id})"

    # Store metrics in cache for monitoring
    store_job_metric(job_class, "success", duration_ms)
  rescue StandardError => e
    duration_ms = ((Time.current - start_time) * 1000).round(2)
    Rails.logger.error "[JobMonitor] Failed #{job_class} after #{duration_ms}ms (job_id: #{job_id}): #{e.message}"

    store_job_metric(job_class, "failure", duration_ms)
    raise
  end

  def track_job_failure(error)
    job_class = self.class.name
    error_message = error.message
    error_class = error.class.name

    Rails.logger.error "[JobMonitor] #{job_class} failed (job_id: #{job_id}): #{error_class} - #{error_message}"

    # Store failure metrics
    store_job_failure(job_class, error_class, error_message)

    # Re-raise to allow normal error handling
    raise
  end

  def store_job_metric(job_class, status, duration_ms)
    key = "job_metrics:#{job_class}:#{Date.current.iso8601}"
    metrics = Rails.cache.read(key) || { success: 0, failure: 0, total_duration_ms: 0, count: 0 }

    metrics[status.to_sym] = (metrics[status.to_sym] || 0) + 1
    metrics[:total_duration_ms] = (metrics[:total_duration_ms] || 0) + duration_ms
    metrics[:count] = (metrics[:count] || 0) + 1
    metrics[:last_updated] = Time.current.iso8601

    Rails.cache.write(key, metrics, expires_in: 7.days)
  end

  def store_job_failure(job_class, error_class, error_message)
    key = "job_failures:#{job_class}:#{Date.current.iso8601}"
    failures = Rails.cache.read(key) || []

    failures << {
      error_class: error_class,
      error_message: error_message.truncate(500),
      timestamp: Time.current.iso8601,
      job_id: job_id
    }

    # Keep only last 100 failures per day
    failures = failures.last(100)

    Rails.cache.write(key, failures, expires_in: 7.days)
  end
end
