class ReadinessChecker
  def check_all
    checks = {
      database: safe_check { check_database },
      cache: safe_check { check_cache },
      storage: safe_check { check_storage }
    }
    ready = checks.values.all? { |c| c[:status] == "ok" }
    { ready: ready, checks: checks }
  end

  private

  def check_database
    start = monotonic_ms
    ActiveRecord::Base.connection.execute("SELECT 1")
    ok_with_duration(start)
  rescue => e
    error_with(e)
  end

  def check_cache
    start = monotonic_ms
    Rails.cache.write("readiness:ping", "pong", expires_in: 1.minute)
    Rails.cache.read("readiness:ping")
    ok_with_duration(start)
  rescue => e
    error_with(e)
  end

  def check_storage
    start = monotonic_ms
    ActiveStorage::Blob.count
    ok_with_duration(start)
  rescue => e
    error_with(e)
  end

  def ok_with_duration(start)
    { status: "ok", duration_ms: (monotonic_ms - start) }
  end

  def error_with(error)
    { status: "error", error: error.message }
  end

  def monotonic_ms
    (Process.clock_gettime(Process::CLOCK_MONOTONIC) * 1000).round(2)
  end

  def safe_check
    yield
  rescue => e
    error_with(e)
  end
end
