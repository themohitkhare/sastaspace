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

  test "subscribe_to_events logs request.failed events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.failed", {
      controller: "inventory_items",
      action: "create",
      error: "StandardError",
      error_message: "Validation failed",
      duration_ms: 5.0,
      request_id: "test-fail-123",
      user_id: 1
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"failed\""
    assert_includes logs, "inventory_items"
    assert_includes logs, "Validation failed"
    assert_includes logs, "test-fail-123"
  end

  test "subscribe_to_events logs cache_read events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    start_time = Time.current
    finish_time = start_time + 0.01.seconds

    ActiveSupport::Notifications.instrument("cache_read.active_support", {
      hit: true,
      key: "test:cache:key"
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"read\""
    assert_includes logs, "\"metric_type\":\"cache\""
    assert_includes logs, "\"hit\":true"
    assert_includes logs, "test:cache:key"
  end

  test "subscribe_to_events logs cache_write events" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    start_time = Time.current
    finish_time = start_time + 0.01.seconds

    ActiveSupport::Notifications.instrument("cache_write.active_support", {
      key: "test:cache:write:key"
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"type\":\"write\""
    assert_includes logs, "\"metric_type\":\"cache\""
    assert_includes logs, "test:cache:write:key"
  end

  test "subscribe_to_events logs cache_read with hit false" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("cache_read.active_support", {
      hit: false,
      key: "test:cache:miss"
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "\"hit\":false"
    assert_includes logs, "test:cache:miss"
  end

  test "log_metric formats JSON correctly" do
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "show",
      status: 200,
      duration_ms: 10.5,
      request_id: "test-json",
      user_id: 42
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    # Verify JSON structure
    assert_includes logs, "\"timestamp\""
    assert_includes logs, "\"level\":\"METRIC\""
    assert_includes logs, "\"metric_type\":\"request\""
    assert_includes logs, "\"data\""
    assert_includes logs, "\"user_id\":42"
  end

  test "reset! handles nil subscriptions gracefully" do
    # Reset should work even if subscriptions is nil
    MetricsLogger.instance_variable_set(:@subscriptions, nil)
    MetricsLogger.instance_variable_set(:@subscribed, false)

    assert_nothing_raised do
      MetricsLogger.reset!
    end

    # Should be able to subscribe after reset
    io = StringIO.new
    Rails.logger = Logger.new(io)
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "test",
      action: "index",
      status: 200,
      duration_ms: 1.0,
      request_id: "test-after-nil-reset",
      user_id: nil
    }) { }

    sleep 0.1
    io.rewind
    logs = io.read

    assert_includes logs, "test-after-nil-reset"
  end
end
