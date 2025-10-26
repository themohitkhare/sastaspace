require "test_helper"

class RedisIntegrationTest < ActiveSupport::TestCase
  test "redis connection works" do
    assert $redis.ping == "PONG"
  end

  test "cache store uses redis" do
    Rails.cache.write("test_key", "test_value", expires_in: 1.minute)
    assert_equal "test_value", Rails.cache.read("test_key")
  end

  test "active job uses redis queue" do
    job = HealthChecker::TestHealthJob.perform_later("test")
    assert job.job_id.present?
  end

  test "redis namespace isolation" do
    # Write to cache
    Rails.cache.write("namespace_test", "value")

    # Verify it's in the correct namespace
    keys = $redis.keys("sastaspace:cache:test:*")
    assert keys.any? { |key| key.include?("namespace_test") }
  end
end
