class ApplicationJob < ActiveJob::Base
  # Automatically retry jobs that encountered a deadlock
  retry_on ActiveRecord::Deadlocked, wait: ->(execution) { execution * 2 }, attempts: 3

  # Most jobs are safe to ignore if the underlying records are no longer available
  discard_on ActiveJob::DeserializationError

  # Don't use broad retry_on StandardError - let individual jobs decide their retry strategy
  # Critical errors like RecordNotFound should bubble up immediately

  around_perform :with_job_logging

  private

  def with_job_logging
    Rails.logger.info "Starting #{self.class.name} with args: #{arguments.inspect}"
    start_time = Time.current

    yield

    duration = Time.current - start_time
    Rails.logger.info "Completed #{self.class.name} in #{duration.round(2)}s"
  rescue => e
    duration = Time.current - start_time
    Rails.logger.error "#{self.class.name} failed after #{duration.round(2)}s: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")
    raise
  end
end
