# Instrumentation concern for collecting metrics
module Instrumentation
  extend ActiveSupport::Concern

  included do
    around_action :instrument_request, if: -> { respond_to?(:around_action) }
  end

  private

  def instrument_request
    start_time = Time.current

    ActiveSupport::Notifications.instrument("request.started", {
      controller: self.class.name,
      action: action_name,
      request_id: request.env["REQUEST_ID"],
      user_id: current_user&.id
    })

    yield

    duration = ((Time.current - start_time) * 1000).round(2)

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: self.class.name,
      action: action_name,
      request_id: request.env["REQUEST_ID"],
      user_id: current_user&.id,
      status: response.status,
      duration_ms: duration
    })
  rescue => e
    duration = ((Time.current - start_time) * 1000).round(2)

    ActiveSupport::Notifications.instrument("request.failed", {
      controller: self.class.name,
      action: action_name,
      request_id: request.env["REQUEST_ID"],
      user_id: current_user&.id,
      error: e.class.name,
      error_message: e.message,
      duration_ms: duration
    })

    raise
  end
end
