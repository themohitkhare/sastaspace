require "test_helper"

class RateLimiterNullStoreTest < ActiveSupport::TestCase
  test "allowed? always true when using NullStore backend" do
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::NullStore.new
    limiter = RateLimiter.new(namespace: "nilstore", period: 60, limit: 1)
    assert_equal true, limiter.allowed?("key1")
    assert_equal true, limiter.allowed?("key1")
  ensure
    Rails.cache = original_cache
  end
end


