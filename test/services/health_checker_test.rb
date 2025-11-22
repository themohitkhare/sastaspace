require "test_helper"

class HealthCheckerTest < ActiveSupport::TestCase
  teardown do
    # Clean up all stubs to prevent interference with other tests
    ActiveRecord::Base.connection.unstub_all if ActiveRecord::Base.connection.respond_to?(:unstub_all)
    Rails.cache.unstub_all if Rails.cache.respond_to?(:unstub_all)
    HealthChecker.unstub_all if HealthChecker.respond_to?(:unstub_all)
  end

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
    assert_includes status[:error], "Cache read/write failed"
  end

  test "cache_status unhealthy on exception" do
    Rails.cache.stubs(:write).raises(StandardError.new("Cache error"))
    status = HealthChecker.cache_status
    assert_equal "unhealthy", status[:status]
    assert_includes status[:error], "Cache error"
  end

  test "jobs_status healthy when Sidekiq is available" do
    # Stub Sidekiq.redis to simulate successful connection
    if defined?(Sidekiq)
      mock_redis = mock
      mock_redis.stubs(:ping).returns("PONG")
      Sidekiq.stubs(:redis).yields(mock_redis)
    else
      # Fallback: stub Redis directly
      mock_redis = mock
      mock_redis.stubs(:ping).returns("PONG")
      mock_redis.stubs(:close)
      Redis.stubs(:new).returns(mock_redis)
    end

    status = HealthChecker.jobs_status
    assert_equal "healthy", status[:status]
    assert_includes status[:message], "operational"
  end

  test "jobs_status unhealthy when Sidekiq/Redis fails" do
    # Stub Sidekiq.redis to raise an error
    if defined?(Sidekiq)
      Sidekiq.stubs(:redis).raises(StandardError.new("redis connection failed"))
    else
      Redis.stubs(:new).raises(StandardError.new("redis connection failed"))
    end

    status = HealthChecker.jobs_status
    assert_equal "unhealthy", status[:status]
    assert_includes status[:error], "redis connection failed"
  end

  test "jobs_status uses Redis directly when Sidekiq not defined" do
    # Temporarily hide Sidekiq if it exists
    original_sidekiq = Object.const_get(:Sidekiq) if defined?(Sidekiq)
    Object.send(:remove_const, :Sidekiq) if defined?(Sidekiq)

    begin
      mock_redis = mock
      mock_redis.stubs(:ping).returns("PONG")
      mock_redis.stubs(:close)
      Redis.stubs(:new).returns(mock_redis)

      status = HealthChecker.jobs_status
      assert_equal "healthy", status[:status]
      assert_includes status[:message], "Redis operational"
    ensure
      # Restore Sidekiq if it was defined
      Object.const_set(:Sidekiq, original_sidekiq) if original_sidekiq
    end
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
