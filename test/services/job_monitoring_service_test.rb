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
end
