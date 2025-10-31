require "test_helper"

class RateLimiterCountNamespaceTest < ActiveSupport::TestCase
  setup do
    # Ensure memory store has some data so bypass check doesn't trigger
    RateLimiter.memory_store["_initialized"] = { expires_at: Time.now + 1.hour }
  end

  test "count reflects number of allowed calls within bucket" do
    limiter = RateLimiter.new(limit: 5, period: 60, namespace: "test")
    identifier = "user-1"
    3.times { assert limiter.allowed?(identifier) }
    assert_equal 3, limiter.count(identifier)
  end

  test "separate namespaces do not share counters" do
    a = RateLimiter.new(limit: 5, period: 60, namespace: "ns-a")
    b = RateLimiter.new(limit: 5, period: 60, namespace: "ns-b")
    id = "ip-1"
    2.times { assert a.allowed?(id) }
    4.times { assert b.allowed?(id) }
    assert_equal 2, a.count(id)
    assert_equal 4, b.count(id)
  end
end
