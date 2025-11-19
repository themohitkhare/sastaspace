# Job monitoring configuration
# Sidekiq monitoring is available via Mission Control Jobs at /admin/jobs/monitor

Rails.application.config.after_initialize do
  # Verify Sidekiq is available
  if defined?(Sidekiq)
    Rails.logger.info "[Sidekiq] ✓ Sidekiq detected and configured"
    Rails.logger.info "[Sidekiq] Monitor jobs at /admin/jobs/monitor (Mission Control Jobs)"
  else
    Rails.logger.warn "[Sidekiq] ⚠ Sidekiq not detected - background jobs may not work"
  end
end
