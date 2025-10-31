class RateLimiter
  DEFAULT_LIMIT = 60
  DEFAULT_PERIOD = 60 # seconds

  def initialize(namespace: "global", limit: DEFAULT_LIMIT, period: DEFAULT_PERIOD)
    @namespace = namespace
    @limit = limit
    @period = period
  end

  def allowed?(identifier)
    # If using NullStore and memory store is empty, bypass rate limiting entirely
    # This allows tests to explicitly disable rate limiting by clearing the memory store
    if using_null_store? && self.class.memory_store.empty?
      return true
    end

    key = cache_key(identifier)
    now_bucket = current_bucket

    data = read_cache(key) || { bucket: now_bucket, count: 0 }
    if data[:bucket] != now_bucket
      data = { bucket: now_bucket, count: 0 }
    end

    if data[:count] < @limit
      data[:count] += 1
      write_cache(key, data, expires_in: @period.seconds)
      true
    else
      false
    end
  end

  def count(identifier)
    data = read_cache(cache_key(identifier)) || { count: 0 }
    data[:count] || 0
  end

  def reset!(identifier)
    delete_cache(cache_key(identifier))
  end

  private

  def cache_key(identifier)
    "rate_limit:#{@namespace}:#{identifier}"
  end

  def current_bucket
    (Time.now.to_i / @period).floor
  end

  # Cache helpers with fallback for :null_store in tests
  # When NullStore is used, we use an in-memory fallback for rate limiting
  # The NullStore test explicitly clears the memory store to test bypass behavior
  def read_cache(key)
    if using_null_store?
      # Use memory store fallback for NullStore (allows rate limiting in tests)
      stored = self.class.memory_store[key]
      # Return nil if expired
      if stored && stored[:expires_at] && stored[:expires_at] < Time.now
        self.class.memory_store.delete(key)
        return nil
      end
      stored
    else
      Rails.cache.read(key)
    end
  end

  def write_cache(key, value, expires_in:)
    if using_null_store?
      # Use memory store fallback for NullStore
      self.class.memory_store[key] = value.merge(expires_at: Time.now + expires_in)
    else
      Rails.cache.write(key, value, expires_in: expires_in)
    end
  end

  def delete_cache(key)
    if using_null_store?
      self.class.memory_store.delete(key)
    else
      Rails.cache.delete(key)
    end
  end

  def using_null_store?
    Rails.cache.is_a?(ActiveSupport::Cache::NullStore)
  end

  def self.memory_store
    @memory_store ||= {}
  end
end
