# Metrics logger for ActiveSupport::Notifications
class MetricsLogger
  def self.subscribe_to_events
    # Subscribe to request events
    ActiveSupport::Notifications.subscribe("request.completed") do |name, start, finish, id, payload|
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

    ActiveSupport::Notifications.subscribe("request.failed") do |name, start, finish, id, payload|
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
    ActiveSupport::Notifications.subscribe("perform.active_job") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("job", {
        type: "completed",
        job_class: payload[:job].class.name,
        duration_ms: duration,
        queue_name: payload[:job].queue_name
      })
    end

    ActiveSupport::Notifications.subscribe("enqueue.active_job") do |name, start, finish, id, payload|
      log_metric("job", {
        type: "enqueued",
        job_class: payload[:job].class.name,
        queue_name: payload[:job].queue_name
      })
    end

    # Subscribe to cache events
    ActiveSupport::Notifications.subscribe("cache_read.active_support") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("cache", {
        type: "read",
        hit: payload[:hit],
        duration_ms: duration,
        key: payload[:key]
      })
    end

    ActiveSupport::Notifications.subscribe("cache_write.active_support") do |name, start, finish, id, payload|
      duration = ((finish - start) * 1000).round(2)

      log_metric("cache", {
        type: "write",
        duration_ms: duration,
        key: payload[:key]
      })
    end
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
