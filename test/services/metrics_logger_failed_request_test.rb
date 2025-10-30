require "test_helper"

class MetricsLoggerFailedRequestTest < ActiveSupport::TestCase
  test "logs failed request events" do
    io = StringIO.new
    original = Rails.logger
    Rails.logger = Logger.new(io)
    begin
      MetricsLogger.subscribe_to_events
      ActiveSupport::Notifications.instrument("request.failed", {
        controller: "inventory_items",
        action: "create",
        error: "RuntimeError",
        error_message: "boom",
        duration_ms: 4.2,
        request_id: "abc",
        user_id: 1
      }) { }
      io.rewind
      logs = io.read
      assert_includes logs, "\"type\":\"failed\""
      assert_includes logs, "inventory_items"
      assert_includes logs, "boom"
    ensure
      Rails.logger = original
    end
  end
end


