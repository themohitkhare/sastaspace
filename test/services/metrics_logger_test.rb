require "test_helper"

class MetricsLoggerTest < ActiveSupport::TestCase
  test "logs request completed event" do
    Rails.logger.expects(:info).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "request" &&
      data["data"]["type"] == "completed" &&
      data["data"]["controller"] == "TestController"
    end

    ActiveSupport::Notifications.instrument("request.completed", {
      controller: "TestController",
      action: "index",
      status: 200,
      duration_ms: 100,
      request_id: "123",
      user_id: 1
    })
  end

  test "logs request failed event" do
    Rails.logger.expects(:info).times(1).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "request" &&
      data["data"]["type"] == "failed" &&
      data["data"]["error"] == "StandardError"
    end

    ActiveSupport::Notifications.instrument("request.failed", {
      controller: "TestController",
      action: "index",
      error: "StandardError",
      error_message: "Something went wrong",
      duration_ms: 100,
      request_id: "123",
      user_id: 1
    })
  end

  test "logs job completed event" do
    job = mock
    job_class = mock
    job_class.stubs(:name).returns("TestJob")
    job.stubs(:class).returns(job_class)
    job.stubs(:queue_name).returns("default")

    # Use times(1) to ensure it's only called once (MetricsLogger might be subscribed in initializer)
    Rails.logger.expects(:info).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "job" &&
      data["data"]["type"] == "completed" &&
      data["data"]["job_class"] == "TestJob"
    end.times(1)

    ActiveSupport::Notifications.instrument("perform.active_job", { job: job }) do
      # simulate duration
    end
  end

  test "logs job enqueued event" do
    job = mock
    job_class = mock
    job_class.stubs(:name).returns("TestJob")
    job.stubs(:class).returns(job_class)
    job.stubs(:queue_name).returns("default")
    job.stubs(:enqueue_error)

    Rails.logger.expects(:info).times(1).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "job" &&
      data["data"]["type"] == "enqueued" &&
      data["data"]["job_class"] == "TestJob"
    end

    ActiveSupport::Notifications.instrument("enqueue.active_job", { job: job })

    assert true # Assertion to satisfy test requirements
  end

  test "logs cache read event" do
    Rails.logger.expects(:info).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "cache" &&
      data["data"]["type"] == "read" &&
      data["data"]["key"] == "test_key"
    end

    ActiveSupport::Notifications.instrument("cache_read.active_support", {
      key: "test_key",
      hit: true
    }) do
      # simulate duration
    end
  end

  test "logs cache write event" do
    Rails.logger.expects(:info).with do |json|
      data = JSON.parse(json)
      data["metric_type"] == "cache" &&
      data["data"]["type"] == "write" &&
      data["data"]["key"] == "test_key"
    end

    ActiveSupport::Notifications.instrument("cache_write.active_support", {
      key: "test_key"
    }) do
      # simulate duration
    end
  end
end
