# Initialize metrics logging
Rails.application.config.after_initialize do
  MetricsLogger.subscribe_to_events
end
