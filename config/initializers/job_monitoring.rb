# Job monitoring configuration
# Sidekiq monitoring is available via Sidekiq::Web at /admin/jobs

Rails.application.config.after_initialize do
  # Verify Sidekiq is available
  if defined?(Sidekiq)
    # Only log at startup if log level allows (use debug to avoid noise)
    Rails.logger.debug "[Sidekiq] ✓ Sidekiq detected and configured"
    Rails.logger.debug "[Sidekiq] Monitor jobs at /admin/jobs (Sidekiq::Web - admin only)"
  else
    Rails.logger.warn "[Sidekiq] ⚠ Sidekiq not detected - background jobs may not work"
  end
end
