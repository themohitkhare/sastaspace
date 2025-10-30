require "test_helper"

class RateLimiterTest < ActiveSupport::TestCase
  setup do
    Rails.cache.clear
  end

  test "allowed? permits up to the limit within period" do
    limiter = RateLimiter.new(namespace: "auth", limit: 3, period: 60)
    key = "user-1"

    assert limiter.allowed?(key)
    assert limiter.allowed?(key)
    assert limiter.allowed?(key)
    assert_not limiter.allowed?(key), "Should block after reaching limit"
    assert_equal 3, limiter.count(key)
  end

  test "reset! clears the counter" do
    limiter = RateLimiter.new(namespace: "api", limit: 1, period: 60)
    key = "ip:127.0.0.1"

    assert limiter.allowed?(key)
    assert_not limiter.allowed?(key)

    limiter.reset!(key)

    assert limiter.allowed?(key), "Should allow again after reset"
  end

  test "bucket rollover resets count for new period" do
    limiter = RateLimiter.new(namespace: "test", limit: 1, period: 1)
    key = "any"

    assert limiter.allowed?(key)
    sleep 1.1
    assert limiter.allowed?(key), "New time bucket should allow again"
  end
end
