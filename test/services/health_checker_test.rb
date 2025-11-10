require "test_helper"

class HealthCheckerTest < ActiveSupport::TestCase
  test "database_status healthy" do
    ActiveRecord::Base.connection.stubs(:execute).with("SELECT 1").returns([ [ 1 ] ])
    status = HealthChecker.database_status
    assert_equal "healthy", status[:status]
  end

  test "database_status unhealthy on error" do
    ActiveRecord::Base.connection.stubs(:execute).raises(StandardError.new("db down"))
    status = HealthChecker.database_status
    assert_equal "unhealthy", status[:status]
    assert_includes status[:error], "db down"
  end

  test "cache_status healthy" do
    Rails.cache.stubs(:write).returns(true)
    Rails.cache.stubs(:read).returns("ok")
    status = HealthChecker.cache_status
    assert_equal "healthy", status[:status]
  end

  test "cache_status unhealthy when read fails" do
    Rails.cache.stubs(:write).returns(true)
    Rails.cache.stubs(:read).returns(nil)
    status = HealthChecker.cache_status
    assert_equal "unhealthy", status[:status]
  end

  test "jobs_status healthy when job monitoring is available" do
    JobMonitoringService.stubs(:queue_health).returns({
      status: "healthy",
      queues: { "default" => { depth: 0 } },
      workers: { active: 1 },
      alerts: []
    })

    status = HealthChecker.jobs_status
    assert_equal "healthy", status[:status]
    assert_equal "Job queue operational", status[:message]
    assert status[:queue_depth].is_a?(Integer)
    assert status[:workers].is_a?(Integer)
    assert status[:alerts].is_a?(Integer)
  end

  test "jobs_status unhealthy when job monitoring fails" do
    JobMonitoringService.stubs(:queue_health).raises(StandardError.new("queue down"))

    status = HealthChecker.jobs_status
    assert_equal "unhealthy", status[:status]
    assert_includes status[:error], "queue down"
  end

  test "overall_status is healthy when all services are healthy" do
    HealthChecker.stubs(:database_status).returns({ status: "healthy" })
    HealthChecker.stubs(:cache_status).returns({ status: "healthy" })
    HealthChecker.stubs(:jobs_status).returns({ status: "healthy" })

    assert_equal "healthy", HealthChecker.overall_status
  end

  test "overall_status is unhealthy when any service is unhealthy" do
    HealthChecker.stubs(:database_status).returns({ status: "healthy" })
    HealthChecker.stubs(:cache_status).returns({ status: "unhealthy" })
    HealthChecker.stubs(:jobs_status).returns({ status: "healthy" })

    assert_equal "unhealthy", HealthChecker.overall_status
  end

  test "check_all returns comprehensive status" do
    HealthChecker.stubs(:database_status).returns({ status: "healthy" })
    HealthChecker.stubs(:cache_status).returns({ status: "healthy" })
    HealthChecker.stubs(:jobs_status).returns({ status: "healthy" })

    result = HealthChecker.check_all
    assert_equal "healthy", result[:status]
    assert result[:timestamp].present?
    assert result[:services].present?
    assert result[:services][:database].present?
    assert result[:services][:cache].present?
    assert result[:services][:jobs].present?
  end
end
