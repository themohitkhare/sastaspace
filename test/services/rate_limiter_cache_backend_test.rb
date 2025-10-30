require "test_helper"

class RateLimiterCacheBackendTest < ActiveSupport::TestCase
  test "uses Rails.cache backend when not NullStore" do
    original_cache = Rails.cache
    begin
      Rails.cache = ActiveSupport::Cache::MemoryStore.new
      limiter = RateLimiter.new(namespace: "cache-backend", limit: 2, period: 60)
      id = "abc"
      assert limiter.allowed?(id)
      assert limiter.allowed?(id)
      refute limiter.allowed?(id)
      assert_equal 2, limiter.count(id)
    ensure
      Rails.cache = original_cache
    end
  end
end


