require "test_helper"

class RateLimiterNullStoreTest < ActiveSupport::TestCase
  test "allowed? always true when using NullStore backend" do
    original_cache = Rails.cache
    # Clear the memory store to test bypass behavior
    RateLimiter.memory_store.clear

    Rails.cache = ActiveSupport::Cache::NullStore.new
    limiter = RateLimiter.new(namespace: "nilstore", period: 60, limit: 1)

    # When memory store is empty, NullStore should bypass rate limiting
    # This simulates the scenario where NullStore is used explicitly to disable rate limiting
    assert_equal true, limiter.allowed?("key1")
    assert_equal true, limiter.allowed?("key1")
  ensure
    Rails.cache = original_cache
    RateLimiter.memory_store.clear
  end
end
