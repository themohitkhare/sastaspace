require "test_helper"

class JobMonitoringServiceTest < ActiveSupport::TestCase
  def setup
    # Use memory store for caching tests
    @original_cache_store = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new
  end

  def teardown
    Rails.cache = @original_cache_store if @original_cache_store
  end

  test "queue_health returns unavailable when solid queue tables don't exist" do
    # Mock that tables don't exist by stubbing the internal method calls
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:worker_metrics).returns({ total: 0, active: 0, stale: 0, processes: [] })
    JobMonitoringService.stubs(:job_metrics).returns({})
    JobMonitoringService.stubs(:failure_metrics).returns({ total: 0, failure_rate: 0.0, failure_rate_percent: 0.0, by_job_class: {}, time_window_seconds: 3600 })
    JobMonitoringService.stubs(:active_alerts).returns([])
    JobMonitoringService.stubs(:overall_status).returns("unavailable")

    # Force the rescue block by raising an error
    JobMonitoringService.stubs(:all_queue_names).raises(ActiveRecord::StatementInvalid.new("relation \"solid_queue_jobs\" does not exist"))

    health = JobMonitoringService.queue_health

    assert_equal "unavailable", health[:status]
    assert_equal "Solid Queue tables not initialized", health[:error]
    assert_equal({}, health[:queues])
    assert_equal({ total: 0, active: 0, stale: 0, processes: [] }, health[:workers])
  end

  test "queue_health handles ActiveRecord errors gracefully" do
    # Simulate ActiveRecord error in queue_health
    JobMonitoringService.stubs(:all_queue_names).raises(ActiveRecord::StatementInvalid.new("relation \"solid_queue_jobs\" does not exist"))

    health = JobMonitoringService.queue_health

    assert_equal "unavailable", health[:status]
  end

  test "queue_metrics returns empty hash when no queues exist" do
    JobMonitoringService.stubs(:all_queue_names).returns([])

    metrics = JobMonitoringService.queue_metrics

    assert_equal({}, metrics)
  end

  test "worker_metrics returns empty when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    metrics = JobMonitoringService.worker_metrics

    assert_equal({ total: 0, active: 0, stale: 0, processes: [] }, metrics)
  end

  test "job_metrics returns empty hash when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    metrics = JobMonitoringService.job_metrics

    assert_equal({}, metrics)
  end

  test "job_class_metrics returns empty hash when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    metrics = JobMonitoringService.job_class_metrics("TestJob")

    assert_equal({}, metrics)
  end

  test "failure_metrics returns zero values when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    metrics = JobMonitoringService.failure_metrics

    assert_equal 0, metrics[:total]
    assert_equal 0.0, metrics[:failure_rate]
    assert_equal 0.0, metrics[:failure_rate_percent]
    assert_equal({}, metrics[:by_job_class])
  end

  test "capacity_metrics returns zero values when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    metrics = JobMonitoringService.capacity_metrics

    assert_equal({}, metrics[:queue_depths])
    assert_equal({ total_workers: 0, active_workers: 0 }, metrics[:worker_capacity])
    assert_equal({ jobs_per_minute: 0, estimated_time_to_clear_minutes: 0 }, metrics[:processing_rate])
  end

  test "all_queue_names returns empty array when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    queues = JobMonitoringService.send(:all_queue_names)

    assert_equal [], queues
  end

  test "queue_depth returns zero when solid queue unavailable" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(false)

    depth = JobMonitoringService.send(:queue_depth, "default")

    assert_equal 0, depth
  end

  test "median calculates median correctly" do
    assert_equal 3.0, JobMonitoringService.send(:median, [ 1, 2, 3, 4, 5 ])
    assert_equal 2.5, JobMonitoringService.send(:median, [ 1, 2, 3, 4 ])
    assert_equal 5.0, JobMonitoringService.send(:median, [ 5 ])
  end

  test "percentile calculates percentile correctly" do
    array = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]
    # For 10 elements, 95th percentile is index 9 (0.95 * 9 = 8.55, ceil = 9)
    assert_equal 10, JobMonitoringService.send(:percentile, array, 0.95)
    # For 10 elements, 90th percentile is index 9 (0.90 * 9 = 8.1, ceil = 9)
    assert_equal 10, JobMonitoringService.send(:percentile, array, 0.90)
    # For 10 elements, 50th percentile is index 5 (0.50 * 9 = 4.5, ceil = 5)
    assert_equal 6, JobMonitoringService.send(:percentile, array, 0.50)
  end

  test "active_alerts returns empty array when no alerts" do
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.01,
      failure_rate_percent: 1.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal [], alerts
  end

  test "active_alerts detects queue depth warnings" do
    JobMonitoringService.stubs(:all_queue_names).returns([ "default" ])
    JobMonitoringService.stubs(:queue_depth).with("default").returns(150) # Above warning threshold
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.01,
      failure_rate_percent: 1.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "warning", alerts.first[:level]
    assert_equal "queue_depth", alerts.first[:type]
    assert_equal "default", alerts.first[:queue]
  end

  test "active_alerts detects queue depth critical" do
    JobMonitoringService.stubs(:all_queue_names).returns([ "default" ])
    JobMonitoringService.stubs(:queue_depth).with("default").returns(600) # Above critical threshold
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.01,
      failure_rate_percent: 1.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "critical", alerts.first[:level]
    assert_equal "queue_depth", alerts.first[:type]
  end

  test "active_alerts detects failure rate warnings" do
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.06, # Above warning threshold (5%)
      failure_rate_percent: 6.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "warning", alerts.first[:level]
    assert_equal "failure_rate", alerts.first[:type]
  end

  test "overall_status returns healthy when no alerts" do
    JobMonitoringService.stubs(:active_alerts).returns([])

    status = JobMonitoringService.send(:overall_status)

    assert_equal "healthy", status
  end

  test "overall_status returns warning when warnings present" do
    JobMonitoringService.stubs(:active_alerts).returns([
      { level: "warning", type: "queue_depth" }
    ])

    status = JobMonitoringService.send(:overall_status)

    assert_equal "warning", status
  end

  test "overall_status returns critical when critical alerts present" do
    JobMonitoringService.stubs(:active_alerts).returns([
      { level: "critical", type: "queue_depth" }
    ])

    status = JobMonitoringService.send(:overall_status)

    assert_equal "critical", status
  end

  test "queue_metrics with specific queue_name" do
    JobMonitoringService.stubs(:all_queue_names).returns([ "default", "high_priority" ])
    JobMonitoringService.stubs(:queue_depth).with("default").returns(10)
    JobMonitoringService.stubs(:ready_job_count).with("default").returns(5)
    JobMonitoringService.stubs(:claimed_job_count).with("default").returns(3)
    JobMonitoringService.stubs(:scheduled_job_count).with("default").returns(2)
    JobMonitoringService.stubs(:blocked_job_count).with("default").returns(0)
    JobMonitoringService.stubs(:queue_paused?).with("default").returns(false)

    metrics = JobMonitoringService.queue_metrics(queue_name: "default")

    assert_equal 1, metrics.keys.count
    assert metrics.key?("default")
    assert_equal 10, metrics["default"][:depth]
  end

  test "queue_health re-raises non-solid_queue errors" do
    JobMonitoringService.stubs(:all_queue_names).raises(ActiveRecord::StatementInvalid.new("other error"))

    assert_raises(ActiveRecord::StatementInvalid) do
      JobMonitoringService.queue_health
    end
  end

  test "worker_metrics handles processes with different statuses" do
    return unless defined?(SolidQueue::Process)

    # This test would require actual SolidQueue setup
    # For now, test the rescue path
    JobMonitoringService.stubs(:solid_queue_available?).returns(true)
    SolidQueue::Process.stubs(:where).raises(ActiveRecord::StatementInvalid.new("error"))

    metrics = JobMonitoringService.worker_metrics

    assert_equal({ total: 0, active: 0, stale: 0, processes: [] }, metrics)
  end

  test "process_alive returns true for recent heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(1.minute.ago)
    now = Time.current

    assert JobMonitoringService.send(:process_alive?, process, now)
  end

  test "process_alive returns false for old heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(5.minutes.ago)
    now = Time.current

    assert_not JobMonitoringService.send(:process_alive?, process, now)
  end

  test "process_stale returns true for old heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(5.minutes.ago)
    now = Time.current

    assert JobMonitoringService.send(:process_stale?, process, now)
  end

  test "process_stale returns false for recent heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(1.minute.ago)
    now = Time.current

    assert_not JobMonitoringService.send(:process_stale?, process, now)
  end

  test "process_status returns critical for very old heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(10.minutes.ago)
    now = Time.current

    assert_equal "critical", JobMonitoringService.send(:process_status, process, now)
  end

  test "process_status returns stale for moderately old heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(3.minutes.ago)
    now = Time.current

    assert_equal "stale", JobMonitoringService.send(:process_status, process, now)
  end

  test "process_status returns healthy for recent heartbeat" do
    process = mock
    process.stubs(:last_heartbeat_at).returns(1.minute.ago)
    now = Time.current

    assert_equal "healthy", JobMonitoringService.send(:process_status, process, now)
  end

  test "active_alerts detects stale workers" do
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.01,
      failure_rate_percent: 1.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: [
        { name: "worker1", status: "stale" },
        { name: "worker2", status: "healthy" }
      ]
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "warning", alerts.first[:level]
    assert_equal "stale_workers", alerts.first[:type]
    assert_equal 1, alerts.first[:count]
  end

  test "active_alerts detects stale jobs" do
    job1 = mock
    job1.stubs(:id).returns(1)
    job2 = mock
    job2.stubs(:id).returns(2)

    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.01,
      failure_rate_percent: 1.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([ job1, job2 ])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "warning", alerts.first[:level]
    assert_equal "stale_jobs", alerts.first[:type]
    assert_equal 2, alerts.first[:count]
  end

  test "active_alerts detects failure rate critical" do
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:failure_metrics).returns({
      failure_rate: 0.15, # Above critical threshold (10%)
      failure_rate_percent: 15.0
    })
    JobMonitoringService.stubs(:worker_metrics).returns({
      processes: []
    })
    JobMonitoringService.stubs(:stale_claimed_jobs).returns([])

    alerts = JobMonitoringService.active_alerts

    assert_equal 1, alerts.count
    assert_equal "critical", alerts.first[:level]
    assert_equal "failure_rate", alerts.first[:type]
  end

  test "job_metrics handles empty processing times" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(true)

    # Stub the method chain: where().where.not().pluck()
    # The chain is: completed_jobs.where.not(...).pluck(...)
    # where() returns a relation, then .not() is called on it, then .pluck()
    mock_pluck_relation = mock
    mock_pluck_relation.stubs(:pluck).returns([])

    mock_where_not_relation = mock
    mock_where_not_relation.stubs(:pluck).returns([])

    mock_where_relation = mock
    mock_where_relation.stubs(:count).returns(0)
    # where() returns a relation that responds to not()
    mock_where_result = mock
    mock_where_result.stubs(:not).returns(mock_where_not_relation)
    mock_where_relation.stubs(:where).returns(mock_where_result)

    SolidQueue::Job.stubs(:where).returns(mock_where_relation)

    metrics = JobMonitoringService.job_metrics

    assert metrics.is_a?(Hash), "Metrics should be a hash"
    assert_equal 0, metrics[:completed]
    assert_equal 0, metrics[:average_processing_time_ms]
    assert_equal 0, metrics[:median_processing_time_ms]
    assert metrics.key?(:p95_processing_time_ms), "Should include p95 metric"
    assert metrics.key?(:p99_processing_time_ms), "Should include p99 metric"
  end

  test "job_class_metrics handles zero completed jobs" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(true)
    mock_jobs = mock
    mock_jobs.stubs(:count).returns(0)
    mock_jobs.stubs(:where).returns(mock(count: 0, pluck: []))
    SolidQueue::Job.stubs(:where).returns(mock_jobs)
    SolidQueue::FailedExecution.stubs(:joins).returns(mock(where: mock(count: 0)))

    metrics = JobMonitoringService.job_class_metrics("TestJob")

    assert_equal 0, metrics[:total]
    assert_equal 0, metrics[:completed]
    assert_equal 100.0, metrics[:success_rate]
  end

  test "estimated_clearance_time returns 0 when rate is zero" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(true)
    JobMonitoringService.stubs(:jobs_per_minute).returns(0)
    SolidQueue::ReadyExecution.stubs(:count).returns(10)
    SolidQueue::ScheduledExecution.stubs(:count).returns(5)

    time = JobMonitoringService.send(:estimated_clearance_time)

    assert_equal 0, time
  end

  test "estimated_clearance_time calculates correctly" do
    JobMonitoringService.stubs(:solid_queue_available?).returns(true)
    JobMonitoringService.stubs(:jobs_per_minute).returns(10)
    SolidQueue::ReadyExecution.stubs(:count).returns(50)
    SolidQueue::ScheduledExecution.stubs(:count).returns(30)

    time = JobMonitoringService.send(:estimated_clearance_time)

    assert_equal 8.0, time # (50 + 30) / 10 = 8.0
  end

  test "queue_health includes timestamp" do
    JobMonitoringService.stubs(:all_queue_names).returns([])
    JobMonitoringService.stubs(:worker_metrics).returns({ total: 0, active: 0, stale: 0, processes: [] })
    JobMonitoringService.stubs(:job_metrics).returns({})
    JobMonitoringService.stubs(:failure_metrics).returns({ total: 0, failure_rate: 0.0, failure_rate_percent: 0.0, by_job_class: {}, time_window_seconds: 3600 })
    JobMonitoringService.stubs(:active_alerts).returns([])
    JobMonitoringService.stubs(:overall_status).returns("healthy")

    health = JobMonitoringService.queue_health

    assert health[:timestamp].present?
    assert_match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/, health[:timestamp])
  end

  test "solid_queue_available? caches result" do
    # Reset cache
    JobMonitoringService.instance_variable_set(:@solid_queue_available, nil)

    # First call should check table
    SolidQueue::Job.stubs(:connection).returns(mock(table_exists?: true))
    result1 = JobMonitoringService.send(:solid_queue_available?)

    # Second call should use cache (should not call connection again)
    SolidQueue::Job.expects(:connection).never
    result2 = JobMonitoringService.send(:solid_queue_available?)

    assert_equal result1, result2
  end

  test "solid_queue_available? returns false on error" do
    JobMonitoringService.instance_variable_set(:@solid_queue_available, nil)
    SolidQueue::Job.stubs(:connection).raises(StandardError.new("Connection error"))

    result = JobMonitoringService.send(:solid_queue_available?)

    assert_not result
  end
end
