require "test_helper"
require "json"

class MetricsLoggerTest < ActiveSupport::TestCase
  setup do
    @logger_output = StringIO.new
    Rails.logger.stubs(:info).with { |arg| @logger_output.write(arg.to_s + "\n"); true }
  end

  teardown do
    Rails.logger.unstub(:info) if Rails.logger.respond_to?(:unstub)
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

  test "cache_read logs hit false when cache miss" do
    MetricsLogger.subscribe_to_events

    payload = {
      hit: false,
      key: "test_cache_key"
    }

    ActiveSupport::Notifications.instrument("cache_read.active_support", payload) do
      # Simulate cache read
    end

    sleep 0.1

    output = @logger_output.string
    assert_match(/METRIC/, output)
    assert_match(/cache/, output)
    assert_match(/read/, output)
    # Should include hit: false in the output
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_equal false, parsed["data"]["hit"]
  end

  test "log_metric includes timestamp" do
    data = { test: "value" }
    MetricsLogger.send(:log_metric, "test_metric", data)

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_not_nil parsed["timestamp"]
    assert_match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/, parsed["timestamp"])
  end

  test "log_metric includes level METRIC" do
    data = { test: "value" }
    MetricsLogger.send(:log_metric, "test_metric", data)

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_equal "METRIC", parsed["level"]
  end

  test "perform.active_job calculates duration correctly" do
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

    sleep 0.1

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_not_nil parsed["data"]["duration_ms"]
    assert parsed["data"]["duration_ms"].is_a?(Numeric)
  end

  test "cache_read logs duration correctly" do
    MetricsLogger.subscribe_to_events

    payload = {
      hit: true,
      key: "test_cache_key"
    }

    ActiveSupport::Notifications.instrument("cache_read.active_support", payload) do
      # Simulate cache read
    end

    sleep 0.1

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_not_nil parsed["data"]["duration_ms"]
    assert parsed["data"]["duration_ms"].is_a?(Numeric)
  end

  test "cache_write logs duration correctly" do
    MetricsLogger.subscribe_to_events

    payload = {
      key: "test_cache_key"
    }

    ActiveSupport::Notifications.instrument("cache_write.active_support", payload) do
      # Simulate cache write
    end

    sleep 0.1

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_not_nil parsed["data"]["duration_ms"]
    assert parsed["data"]["duration_ms"].is_a?(Numeric)
  end

  test "enqueue.active_job logs job class and queue name" do
    MetricsLogger.subscribe_to_events

    job = ExportUserDataJob.new
    payload = {
      job: job,
      queue_name: "default"
    }

    ActiveSupport::Notifications.instrument("enqueue.active_job", payload)

    sleep 0.1

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_equal "ExportUserDataJob", parsed["data"]["job_class"]
    assert_equal "default", parsed["data"]["queue_name"]
  end

  test "perform.active_job logs job class and queue name" do
    MetricsLogger.subscribe_to_events

    job = ExportUserDataJob.new
    payload = {
      job: job,
      queue_name: "default"
    }

    ActiveSupport::Notifications.instrument("perform.active_job", payload) do
      # Simulate job execution
    end

    sleep 0.1

    output = @logger_output.string
    json_lines = output.split("\n").select { |line| line.strip.start_with?("{") }
    assert_not_empty json_lines, "Should have at least one JSON log entry"
    parsed = JSON.parse(json_lines.last)
    assert_equal "ExportUserDataJob", parsed["data"]["job_class"]
    assert_equal "default", parsed["data"]["queue_name"]
  end
end
