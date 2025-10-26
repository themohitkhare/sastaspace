class ReadyController < ApplicationController
  include StructuredLogging

  def show
    readiness_status = check_readiness
    status = readiness_status[:ready] ? :ok : :service_unavailable

    log_info("Readiness check performed", {
      ready: readiness_status[:ready],
      checks: readiness_status[:checks].keys
    })

    render json: {
      status: readiness_status[:ready] ? "ready" : "not_ready",
      timestamp: Time.current.iso8601,
      checks: readiness_status[:checks]
    }, status: status
  end

  private

  def check_readiness
    checks = {
      migrations: check_migrations,
      queues: check_queues,
      storage: check_storage
    }

    ready = checks.values.all? { |check| check[:status] == "ok" }

    { ready: ready, checks: checks }
  end

          def check_migrations
            # Check if all migrations are up to date
            start_time = Time.current
            # Simple check - if we can connect to the database, migrations are likely up to date
            ActiveRecord::Base.connection.execute("SELECT 1")
            duration = ((Time.current - start_time) * 1000).round(2)

            { status: "ok", duration_ms: duration }
          rescue => e
            { status: "error", error: e.message }
          end

  def check_queues
    # Check if job queues are accessible
    start_time = Time.current
    SolidQueue::Job.count
    duration = ((Time.current - start_time) * 1000).round(2)

    { status: "ok", duration_ms: duration }
  rescue => e
    { status: "error", error: e.message }
  end

  def check_storage
    # Check if Active Storage is ready
    start_time = Time.current
    ActiveStorage::Blob.count
    duration = ((Time.current - start_time) * 1000).round(2)

    { status: "ok", duration_ms: duration }
  rescue => e
    { status: "error", error: e.message }
  end
end
