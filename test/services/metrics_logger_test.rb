require "test_helper"

class MetricsLoggerTest < ActiveSupport::TestCase
  setup do
    @logger_output = StringIO.new
    Rails.logger.stubs(:info).with { |arg| @logger_output.write(arg.to_s + "\n"); true }
  end

  test "subscribes to request.completed events" do
    MetricsLogger.subscribe_to_events

    payload = {
      controller: "Api::V1::UsersController",
      action: "index",
      status: 200,
      duration_ms: 45.2,
      request_id: "test-123",
      user_id: 1
    }

    ActiveSupport::Notifications.instrument("request.completed", payload)

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/request/, output)
    assert_match(/completed/, output)
  end

  test "subscribes to request.failed events" do
    MetricsLogger.subscribe_to_events

    payload = {
      controller: "Api::V1::UsersController",
      action: "create",
      error: "StandardError",
      error_message: "Something went wrong",
      duration_ms: 12.5,
      request_id: "test-456",
      user_id: 2
    }

    ActiveSupport::Notifications.instrument("request.failed", payload)

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/request/, output)
    assert_match(/failed/, output)
  end

  test "subscribes to perform.active_job events" do
    MetricsLogger.subscribe_to_events

    job = ExportUserDataJob.new
    payload = {
      job: job,
      queue_name: "default"
    }

    start_time = Time.current
    finish_time = start_time + 0.5.seconds

    ActiveSupport::Notifications.instrument("perform.active_job", payload) do
      # Simulate job execution
    end

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/job/, output)
    assert_match(/completed/, output)
  end

  test "subscribes to enqueue.active_job events" do
    MetricsLogger.subscribe_to_events

    job = ExportUserDataJob.new
    payload = {
      job: job,
      queue_name: "default"
    }

    ActiveSupport::Notifications.instrument("enqueue.active_job", payload)

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/job/, output)
    assert_match(/enqueued/, output)
  end

  test "subscribes to cache_read.active_support events" do
    MetricsLogger.subscribe_to_events

    payload = {
      hit: true,
      key: "test_cache_key"
    }

    start_time = Time.current
    finish_time = start_time + 0.01.seconds

    ActiveSupport::Notifications.instrument("cache_read.active_support", payload) do
      # Simulate cache read
    end

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/cache/, output)
    assert_match(/read/, output)
  end

  test "subscribes to cache_write.active_support events" do
    MetricsLogger.subscribe_to_events

    payload = {
      key: "test_cache_key"
    }

    start_time = Time.current
    finish_time = start_time + 0.01.seconds

    ActiveSupport::Notifications.instrument("cache_write.active_support", payload) do
      # Simulate cache write
    end

    # Give notification time to process
    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/cache/, output)
    assert_match(/write/, output)
  end

  test "log_metric formats data as JSON" do
    data = { test: "value", number: 123 }
    MetricsLogger.send(:log_metric, "test_metric", data)

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/test_metric/, output)
    # Should be valid JSON
    assert_match(/"test":"value"/, output)
  end
end
