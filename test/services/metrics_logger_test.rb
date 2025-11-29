require "test_helper"

class MetricsLoggerTest < ActiveSupport::TestCase
  def setup
    MetricsLogger.reset!
    @original_logger = Rails.logger
    @log_output = StringIO.new
    Rails.logger = Logger.new(@log_output)
  end

  def teardown
    MetricsLogger.reset!
    Rails.logger = @original_logger
  end

  test "subscribe_to_events prevents duplicate subscriptions" do
    MetricsLogger.subscribe_to_events
    initial_count = MetricsLogger.instance_variable_get(:@subscriptions).count

    MetricsLogger.subscribe_to_events # Try to subscribe again
    final_count = MetricsLogger.instance_variable_get(:@subscriptions).count

    assert_equal initial_count, final_count, "Should not create duplicate subscriptions"
  end

  test "subscribe_to_events subscribes to request.completed events" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "TestController",
      action: "index",
      status: 200,
      duration_ms: 50.5,
      request_id: "test-123",
      user_id: 1
    })

    # Give notifications time to process
    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/request/, log_content)
    assert_match(/completed/, log_content)
    assert_match(/TestController/, log_content)
  end

  test "subscribe_to_events subscribes to request.failed events" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.failed", {
      controller: "TestController",
      action: "create",
      error: "StandardError",
      error_message: "Something went wrong",
      duration_ms: 25.0,
      request_id: "test-456",
      user_id: 2
    })

    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/request/, log_content)
    assert_match(/failed/, log_content)
    assert_match(/Something went wrong/, log_content)
  end

  test "subscribe_to_events subscribes to perform.active_job events" do
    MetricsLogger.subscribe_to_events

    # Use a real job instance to avoid mock issues
    job = BackfillEmbeddingsJob.new
    ActiveSupport::Notifications.instrument("perform.active_job", {
      job: job
    })

    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/job/, log_content)
    assert_match(/completed/, log_content)
    assert_match(/BackfillEmbeddingsJob/, log_content)
  end

  test "subscribe_to_events subscribes to enqueue.active_job events" do
    MetricsLogger.subscribe_to_events

    # Use a real job instance to avoid mock issues
    job = BackfillEmbeddingsJob.new
    ActiveSupport::Notifications.instrument("enqueue.active_job", {
      job: job
    })

    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/job/, log_content)
    assert_match(/enqueued/, log_content)
  end

  test "subscribe_to_events subscribes to cache_read.active_support events" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("cache_read.active_support", {
      hit: true,
      key: "test_key"
    })

    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/cache/, log_content)
    assert_match(/read/, log_content)
  end

  test "subscribe_to_events subscribes to cache_write.active_support events" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("cache_write.active_support", {
      key: "test_key"
    })

    sleep 0.1

    log_content = @log_output.string
    assert_match(/METRIC/, log_content)
    assert_match(/cache/, log_content)
    assert_match(/write/, log_content)
  end

  test "reset! unsubscribes all subscriptions" do
    MetricsLogger.subscribe_to_events
    assert MetricsLogger.instance_variable_get(:@subscribed)

    MetricsLogger.reset!

    assert_not MetricsLogger.instance_variable_get(:@subscribed)
    assert_empty MetricsLogger.instance_variable_get(:@subscriptions)
  end

  test "log_metric formats metric data as JSON" do
    MetricsLogger.subscribe_to_events

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "TestController",
      action: "show",
      status: 200,
      duration_ms: 100.0,
      request_id: "test-789",
      user_id: 3
    })

    sleep 0.1

    log_content = @log_output.string
    # Should be valid JSON
    json_match = log_content.match(/\{.*\}/m)
    assert json_match, "Should contain JSON in log output"

    parsed = JSON.parse(json_match[0])
    assert_equal "METRIC", parsed["level"]
    assert_equal "request", parsed["metric_type"]
    assert_equal "completed", parsed["data"]["type"]
    assert_equal "TestController", parsed["data"]["controller"]
  end
end
