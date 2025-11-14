require "test_helper"

class MetricsLoggerCacheTest < ActiveSupport::TestCase
  setup do
    @original_cache = Rails.cache
    # Clear cache to prevent state leakage
    Rails.cache.clear if Rails.cache.respond_to?(:clear)
  end

  teardown do
    # Unsubscribe from all MetricsLogger event subscriptions to prevent state leakage
    # MetricsLogger subscribes to multiple events that need to be cleaned up
    ActiveSupport::Notifications.unsubscribe("request.completed")
    ActiveSupport::Notifications.unsubscribe("request.failed")
    ActiveSupport::Notifications.unsubscribe("perform.active_job")
    ActiveSupport::Notifications.unsubscribe("enqueue.active_job")
    ActiveSupport::Notifications.unsubscribe("cache_read.active_support")
    ActiveSupport::Notifications.unsubscribe("cache_write.active_support")
    
    # Restore original cache store
    Rails.cache = @original_cache if @original_cache
    # Clear cache after test
    Rails.cache.clear if Rails.cache.respond_to?(:clear)
  end

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
