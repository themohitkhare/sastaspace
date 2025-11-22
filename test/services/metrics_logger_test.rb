require "test_helper"

class MetricsLoggerTest < ActiveSupport::TestCase
  setup do
    # Reset subscription state before each test
    MetricsLogger.reset!
    @original_logger = Rails.logger
  end

  teardown do
    # Clean up subscriptions after each test
    MetricsLogger.reset!
    Rails.logger = @original_logger
  end

  test "subscribe_to_events prevents duplicate subscriptions" do
    io = StringIO.new
    Rails.logger = Logger.new(io)

    # First subscription
    MetricsLogger.subscribe_to_events

    # Trigger an event to verify subscription works
    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test-1",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    first_logs = io.read
    first_count = first_logs.scan(/"type":"completed"/).size

    # Second subscription should be ignored (should not create duplicate logs)
    MetricsLogger.subscribe_to_events

    # Clear and trigger again
    io.rewind
    io.truncate(0)

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test-2",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    second_logs = io.read
    second_count = second_logs.scan(/"type":"completed"/).size

    # Should only log once per event, not twice (proving no duplicate subscriptions)
    assert_equal 1, second_count, "Should not create duplicate subscriptions"
  end

  test "subscribe_to_events logs request.completed events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "inventory_items",
      action: "index",
      status: 200,
      duration_ms: 12.5,
      request_id: "test-123",
      user_id: 1
    }) { }

    # Give logger time to write
    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"completed\""
    assert_includes logs, "inventory_items"
    assert_includes logs, "\"status\":200"
    assert_includes logs, "test-123"
  end

  test "subscribe_to_events logs job.enqueued events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    # Create a test job
    job = Class.new(ActiveJob::Base) do
      queue_as :default
    end

    ActiveSupport::Notifications.instrument("enqueue.active_job", {
      job: job.new,
      queue_name: "default"
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"enqueued\""
    assert_includes logs, "\"metric_type\":\"job\""
  end

  test "subscribe_to_events logs job.perform events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    # Create a test job
    job = Class.new(ActiveJob::Base) do
      queue_as :default
    end

    start_time = Time.current
    finish_time = start_time + 0.5.seconds

    ActiveSupport::Notifications.instrument("perform.active_job", {
      job: job.new,
      queue_name: "default"
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"completed\""
    assert_includes logs, "\"metric_type\":\"job\""
  end

  test "reset! clears all subscriptions" do
    io = StringIO.new
    Rails.logger = Logger.new(io)

    # Subscribe and verify it works
    MetricsLogger.subscribe_to_events
    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test-before",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    before_reset_logs = io.read
    assert_includes before_reset_logs, "test-before", "Subscription should work before reset"

    # Reset subscriptions
    MetricsLogger.reset!

    # Clear logger and try again - should not log (subscriptions cleared)
    io.rewind
    io.truncate(0)

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test-after",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    after_reset_logs = io.read

    # Should not contain the new event (subscriptions were cleared)
    assert_not_includes after_reset_logs, "test-after", "Should unsubscribe from events after reset"
  end

  test "reset! allows re-subscription after reset" do
    MetricsLogger.subscribe_to_events
    MetricsLogger.reset!

    # Should be able to subscribe again
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"completed\""
  end
end
