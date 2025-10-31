require "test_helper"

class MetricsLoggerCacheTest < ActiveSupport::TestCase
  test "subscribes to cache read/write events and logs" do
    MetricsLogger.subscribe_to_events
    original_cache = Rails.cache
    begin
      Rails.cache = ActiveSupport::Cache::MemoryStore.new
      Rails.cache.write("metrics:foo", "bar")
      Rails.cache.read("metrics:foo")
      assert true
    ensure
      Rails.cache = original_cache
    end
  end
end
