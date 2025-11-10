require "test_helper"

# Test job class that includes Monitorable
class TestMonitorableJob < ApplicationJob
  include Monitorable

  queue_as :default

  def perform(success: true)
    if success
      Rails.logger.info "Job completed successfully"
    else
      raise StandardError, "Job failed intentionally"
    end
  end
end

class MonitorableTest < ActiveSupport::TestCase
  def setup
    # Use memory store for caching tests
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new
    Rails.cache.clear
  end

  def teardown
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "tracks successful job execution" do
    # Execute job via perform_now to trigger around_perform callback
    TestMonitorableJob.perform_now(success: true)

    # Check that metrics were stored
    key = "job_metrics:TestMonitorableJob:#{Date.current.iso8601}"
    metrics = Rails.cache.read(key)

    assert_not_nil metrics, "Metrics should be stored in cache"
    assert_equal 1, metrics[:success]
    assert_equal 0, metrics[:failure] || 0
    assert metrics[:total_duration_ms] > 0
    assert_equal 1, metrics[:count]
  end

  test "tracks failed job execution" do
    # Execute job via perform_now - it will raise error
    assert_raises(StandardError) do
      TestMonitorableJob.perform_now(success: false)
    end

    # Check that metrics were stored
    key = "job_metrics:TestMonitorableJob:#{Date.current.iso8601}"
    metrics = Rails.cache.read(key)

    assert_not_nil metrics, "Metrics should be stored even on failure"
    assert_equal 0, metrics[:success] || 0
    assert_equal 1, metrics[:failure]
    assert metrics[:total_duration_ms] > 0
    assert_equal 1, metrics[:count]
  end

  test "stores failure details in cache" do
    # Execute job that will fail
    assert_raises(StandardError) do
      TestMonitorableJob.perform_now(success: false)
    end

    # Check that failure was stored
    key = "job_failures:TestMonitorableJob:#{Date.current.iso8601}"
    failures = Rails.cache.read(key)

    assert_not_nil failures, "Failures should be stored in cache"
    assert failures.count > 0
    failure = failures.last
    assert_equal "StandardError", failure[:error_class]
    assert_includes failure[:error_message], "Job failed intentionally"
    assert failure[:job_id].present?
  end

  test "accumulates metrics across multiple executions" do
    # Run job multiple times
    3.times { TestMonitorableJob.perform_now(success: true) }
    2.times do
      assert_raises(StandardError) { TestMonitorableJob.perform_now(success: false) }
    end

    key = "job_metrics:TestMonitorableJob:#{Date.current.iso8601}"
    metrics = Rails.cache.read(key)

    assert_not_nil metrics
    assert_equal 3, metrics[:success]
    assert_equal 2, metrics[:failure]
    assert_equal 5, metrics[:count]
  end

  test "limits failure storage to last 100 failures" do
    # Create 150 failures
    150.times do
      assert_raises(StandardError) { TestMonitorableJob.perform_now(success: false) }
    end

    key = "job_failures:TestMonitorableJob:#{Date.current.iso8601}"
    failures = Rails.cache.read(key)

    assert_not_nil failures
    assert_equal 100, failures.count  # Should be limited to 100
  end

  test "includes Monitorable concern in job" do
    assert TestMonitorableJob.included_modules.include?(Monitorable), "Job should include Monitorable concern"
  end

  test "around_perform callback is registered" do
    # Verify the callback is set up
    callbacks = TestMonitorableJob._perform_callbacks.select { |c| c.filter == :track_job_performance }
    assert callbacks.any?, "around_perform callback should be registered"
  end
end
