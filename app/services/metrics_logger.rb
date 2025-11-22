# Metrics logger for ActiveSupport::Notifications
class MetricsLogger
  @subscribed = false
  @subscriptions = []

  def self.subscribe_to_events
    # Prevent duplicate subscriptions (especially important in tests)
    return if @subscribed
    @subscribed = true

    # Subscribe to request events and store subscription handles
    @subscriptions << ActiveSupport::Notifications.subscribe("request.completed") do |name, start, finish, id, payload|
      log_metric("request", {
        type: "completed",
        controller: payload[:controller],
        action: payload[:action],
        status: payload[:status],
        duration_ms: payload[:duration_ms],
        request_id: payload[:request_id],
        user_id: payload[:user_id]
      })
    end

    @subscriptions << ActiveSupport::Notifications.subscribe("request.failed") do |name, start, finish, id, payload|
      log_metric("request", {
        type: "failed",
        controller: payload[:controller],
        action: payload[:action],
        error: payload[:error],
        error_message: payload[:error_message],
        duration_ms: payload[:duration_ms],
        request_id: payload[:request_id],
        user_id: payload[:user_id]
      })
    end

    # Subscribe to job events
    @subscriptions << ActiveSupport::Notifications.subscribe("perform.active_job") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("job", {
        type: "completed",
        job_class: payload[:job].class.name,
        duration_ms: duration,
        queue_name: payload[:job].queue_name
      })
    end

    @subscriptions << ActiveSupport::Notifications.subscribe("enqueue.active_job") do |name, start, finish, id, payload|
      log_metric("job", {
        type: "enqueued",
        job_class: payload[:job].class.name,
        queue_name: payload[:job].queue_name
      })
    end

    # Subscribe to cache events
    @subscriptions << ActiveSupport::Notifications.subscribe("cache_read.active_support") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("cache", {
        type: "read",
        hit: payload[:hit],
        duration_ms: duration,
        key: payload[:key]
      })
    end

    @subscriptions << ActiveSupport::Notifications.subscribe("cache_write.active_support") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("cache", {
        type: "write",
        duration_ms: duration,
        key: payload[:key]
      })
    end
  end

  # Reset subscription state (for testing)
  def self.reset!
    # Unsubscribe all existing subscriptions
    @subscriptions&.each do |subscription|
      ActiveSupport::Notifications.unsubscribe(subscription)
    end
    @subscriptions = []
    @subscribed = false
  end

  private

  def self.log_metric(metric_type, data)
    Rails.logger.info({
      timestamp: Time.current.iso8601,
      level: "METRIC",
      metric_type: metric_type,
      data: data
    }.to_json)
  end
end
