require "test_helper"

class MetricsLoggerTest < ActiveSupport::TestCase
  setup do
    @io = StringIO.new
    @original_logger = Rails.logger
    Rails.logger = Logger.new(@io)
  end

  teardown do
    Rails.logger = @original_logger
  end

  test "subscribes and logs for request events" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "home",
      action: "index",
      status: 200,
      duration_ms: 12.3,
      request_id: "req-1",
      user_id: 7
    }) { }

    @io.rewind
    logs = @io.read
    assert_includes logs, "\"metric_type\":\"request\""
    assert_includes logs, "\"type\":\"completed\""
    assert_includes logs, "\"controller\":\"home\""
  end

  test "subscribes and logs for job events" do
    MetricsLogger.subscribe_to_events

    job = AnalyzeClothingImageJob.new
    ActiveSupport::Notifications.instrument("enqueue.active_job", { job: job })

    @io.rewind
    logs = @io.read
    assert_includes logs, "\"metric_type\":\"job\""
    assert_includes logs, "\"type\":\"enqueued\""
    assert_includes logs, "AnalyzeClothingImageJob"
  end
end
