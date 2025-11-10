# Service for monitoring background job queue health and performance
# Provides comprehensive monitoring for Solid Queue job system
class JobMonitoringService
  # Default alert thresholds
  DEFAULT_QUEUE_DEPTH_WARNING = 100
  DEFAULT_QUEUE_DEPTH_CRITICAL = 500
  DEFAULT_FAILURE_RATE_WARNING = 0.05 # 5%
  DEFAULT_FAILURE_RATE_CRITICAL = 0.10 # 10%
  DEFAULT_STALE_JOB_WARNING = 1.hour
  DEFAULT_STALE_JOB_CRITICAL = 4.hours
  DEFAULT_WORKER_STALE_WARNING = 2.minutes
  DEFAULT_WORKER_STALE_CRITICAL = 5.minutes

  # Get comprehensive job queue health status
  # @return [Hash] Complete health status with metrics
  def self.queue_health
    {
      status: overall_status,
      timestamp: Time.current.iso8601,
      queues: queue_metrics,
      workers: worker_metrics,
      jobs: job_metrics,
      failures: failure_metrics,
      alerts: active_alerts
    }
  rescue ActiveRecord::StatementInvalid => e
    # Handle case where Solid Queue tables don't exist yet
    if e.message.include?("solid_queue")
      {
        status: "unavailable",
        timestamp: Time.current.iso8601,
        error: "Solid Queue tables not initialized",
        queues: {},
        workers: { total: 0, active: 0, stale: 0, processes: [] },
        jobs: {},
        failures: {},
        alerts: []
      }
    else
      raise
    end
  end

  # Get queue-specific metrics
  # @param queue_name [String, nil] Specific queue name or nil for all queues
  # @return [Hash] Queue metrics
  def self.queue_metrics(queue_name: nil)
    queues = queue_name ? [ queue_name ] : all_queue_names

    queues.each_with_object({}) do |queue, result|
      result[queue] = {
        depth: queue_depth(queue),
        ready: ready_job_count(queue),
        claimed: claimed_job_count(queue),
        scheduled: scheduled_job_count(queue),
        blocked: blocked_job_count(queue),
        paused: queue_paused?(queue)
      }
    end
  end

  # Get worker process metrics
  # @return [Hash] Worker metrics
  def self.worker_metrics
    return { total: 0, active: 0, stale: 0, processes: [] } unless solid_queue_available?

    processes = SolidQueue::Process.where(kind: "Worker").to_a
    now = Time.current

    {
      total: processes.count,
      active: processes.count { |p| process_alive?(p, now) },
      stale: processes.count { |p| process_stale?(p, now) },
      processes: processes.map do |process|
        {
          name: process.name,
          pid: process.pid,
          hostname: process.hostname,
          last_heartbeat: process.last_heartbeat_at.iso8601,
          heartbeat_age_seconds: (now - process.last_heartbeat_at).round(2),
          status: process_status(process, now)
        }
      end
    }
  rescue ActiveRecord::StatementInvalid
    { total: 0, active: 0, stale: 0, processes: [] }
  end

  # Get job performance metrics
  # @param time_window [ActiveSupport::Duration] Time window for metrics (default: 1 hour)
  # @return [Hash] Job performance metrics
  def self.job_metrics(time_window: 1.hour)
    return {} unless solid_queue_available?

    since = time_window.ago

    completed_jobs = SolidQueue::Job.where("finished_at >= ?", since)
    total_completed = completed_jobs.count

    processing_times = completed_jobs
                        .where.not(finished_at: nil, created_at: nil)
                        .pluck(:created_at, :finished_at)
                        .map { |created, finished| (finished - created) * 1000 } # Convert to ms

    {
      completed: total_completed,
      average_processing_time_ms: processing_times.any? ? (processing_times.sum / processing_times.size).round(2) : 0,
      median_processing_time_ms: processing_times.any? ? median(processing_times).round(2) : 0,
      p95_processing_time_ms: processing_times.any? ? percentile(processing_times, 0.95).round(2) : 0,
      p99_processing_time_ms: processing_times.any? ? percentile(processing_times, 0.99).round(2) : 0,
      time_window_seconds: time_window.to_i
    }
  rescue ActiveRecord::StatementInvalid
    {}
  end

  # Get job-specific metrics by class name
  # @param job_class [String] Job class name
  # @param time_window [ActiveSupport::Duration] Time window for metrics
  # @return [Hash] Job-specific metrics
  def self.job_class_metrics(job_class, time_window: 1.hour)
    return {} unless solid_queue_available?

    since = time_window.ago

    jobs = SolidQueue::Job.where(class_name: job_class)
    total = jobs.count
    completed = jobs.where("finished_at >= ?", since).count
    failed = SolidQueue::FailedExecution
              .joins(:job)
              .where("solid_queue_jobs.class_name = ? AND solid_queue_failed_executions.created_at >= ?", job_class, since)
              .count

    processing_times = jobs
                        .where("finished_at >= ? AND finished_at IS NOT NULL AND created_at IS NOT NULL", since)
                        .pluck(:created_at, :finished_at)
                        .map { |created, finished| (finished - created) * 1000 }

    {
      total: total,
      completed: completed,
      failed: failed,
      success_rate: completed.positive? ? ((completed - failed).to_f / completed * 100).round(2) : 100.0,
      average_processing_time_ms: processing_times.any? ? (processing_times.sum / processing_times.size).round(2) : 0,
      time_window_seconds: time_window.to_i
    }
  rescue ActiveRecord::StatementInvalid
    {}
  end

  # Get failure metrics
  # @param time_window [ActiveSupport::Duration] Time window for metrics
  # @return [Hash] Failure metrics
  def self.failure_metrics(time_window: 1.hour)
    return { total: 0, failure_rate: 0.0, failure_rate_percent: 0.0, by_job_class: {}, time_window_seconds: time_window.to_i } unless solid_queue_available?

    since = time_window.ago

    total_jobs = SolidQueue::Job.where("created_at >= ?", since).count
    failed_jobs = SolidQueue::FailedExecution.where("created_at >= ?", since).count
    failure_rate = total_jobs.positive? ? (failed_jobs.to_f / total_jobs).round(4) : 0.0

    failed_by_class = SolidQueue::FailedExecution
                       .joins(:job)
                       .where("solid_queue_failed_executions.created_at >= ?", since)
                       .group("solid_queue_jobs.class_name")
                       .count

    {
      total: failed_jobs,
      failure_rate: failure_rate,
      failure_rate_percent: (failure_rate * 100).round(2),
      by_job_class: failed_by_class,
      time_window_seconds: time_window.to_i
    }
  rescue ActiveRecord::StatementInvalid
    { total: 0, failure_rate: 0.0, failure_rate_percent: 0.0, by_job_class: {}, time_window_seconds: time_window.to_i }
  end

  # Get active alerts based on thresholds
  # @return [Array<Hash>] Array of alert objects
  def self.active_alerts
    alerts = []

    # Check queue depth
    all_queue_names.each do |queue_name|
      depth = queue_depth(queue_name)
      if depth >= DEFAULT_QUEUE_DEPTH_CRITICAL
        alerts << {
          level: "critical",
          type: "queue_depth",
          queue: queue_name,
          value: depth,
          threshold: DEFAULT_QUEUE_DEPTH_CRITICAL,
          message: "Queue #{queue_name} has #{depth} pending jobs (critical threshold: #{DEFAULT_QUEUE_DEPTH_CRITICAL})"
        }
      elsif depth >= DEFAULT_QUEUE_DEPTH_WARNING
        alerts << {
          level: "warning",
          type: "queue_depth",
          queue: queue_name,
          value: depth,
          threshold: DEFAULT_QUEUE_DEPTH_WARNING,
          message: "Queue #{queue_name} has #{depth} pending jobs (warning threshold: #{DEFAULT_QUEUE_DEPTH_WARNING})"
        }
      end
    end

    # Check failure rate
    failure_metrics = self.failure_metrics(time_window: 1.hour)
    if failure_metrics[:failure_rate] >= DEFAULT_FAILURE_RATE_CRITICAL
      alerts << {
        level: "critical",
        type: "failure_rate",
        value: failure_metrics[:failure_rate_percent],
        threshold: DEFAULT_FAILURE_RATE_CRITICAL * 100,
        message: "Job failure rate is #{failure_metrics[:failure_rate_percent]}% (critical threshold: #{DEFAULT_FAILURE_RATE_CRITICAL * 100}%)"
      }
    elsif failure_metrics[:failure_rate] >= DEFAULT_FAILURE_RATE_WARNING
      alerts << {
        level: "warning",
        type: "failure_rate",
        value: failure_metrics[:failure_rate_percent],
        threshold: DEFAULT_FAILURE_RATE_WARNING * 100,
        message: "Job failure rate is #{failure_metrics[:failure_rate_percent]}% (warning threshold: #{DEFAULT_FAILURE_RATE_WARNING * 100}%)"
      }
    end

    # Check for stale workers
    worker_metrics = self.worker_metrics
    stale_workers = worker_metrics[:processes].select { |p| p[:status] == "stale" }
    if stale_workers.any?
      alerts << {
        level: "warning",
        type: "stale_workers",
        count: stale_workers.count,
        workers: stale_workers.map { |w| w[:name] },
        message: "#{stale_workers.count} worker(s) appear stale (no heartbeat in #{DEFAULT_WORKER_STALE_WARNING})"
      }
    end

    # Check for stale jobs (jobs that have been claimed but not finished for too long)
    stale_jobs = stale_claimed_jobs
    if stale_jobs.any?
      alerts << {
        level: "warning",
        type: "stale_jobs",
        count: stale_jobs.count,
        message: "#{stale_jobs.count} job(s) appear stale (claimed but not finished)"
      }
    end

    alerts
  end

  # Get capacity planning metrics
  # @return [Hash] Capacity planning data
  def self.capacity_metrics
    return {
      queue_depths: {},
      worker_capacity: { total_workers: 0, active_workers: 0 },
      processing_rate: { jobs_per_minute: 0, estimated_time_to_clear_minutes: 0 }
    } unless solid_queue_available?

    {
      queue_depths: all_queue_names.each_with_object({}) do |queue, result|
        result[queue] = queue_depth(queue)
      end,
      worker_capacity: {
        total_workers: SolidQueue::Process.where(kind: "Worker").count,
        active_workers: SolidQueue::Process.where(kind: "Worker")
                                            .where("last_heartbeat_at > ?", 1.minute.ago)
                                            .count
      },
      processing_rate: {
        jobs_per_minute: jobs_per_minute,
        estimated_time_to_clear_minutes: estimated_clearance_time
      }
    }
  rescue ActiveRecord::StatementInvalid
    {
      queue_depths: {},
      worker_capacity: { total_workers: 0, active_workers: 0 },
      processing_rate: { jobs_per_minute: 0, estimated_time_to_clear_minutes: 0 }
    }
  end

  private

  def self.solid_queue_available?
    @solid_queue_available ||= begin
      SolidQueue::Job.connection.table_exists?("solid_queue_jobs")
    rescue StandardError
      false
    end
  end

  def self.overall_status
    alerts = active_alerts
    return "critical" if alerts.any? { |a| a[:level] == "critical" }
    return "warning" if alerts.any? { |a| a[:level] == "warning" }
    "healthy"
  end

  def self.all_queue_names
    return [] unless solid_queue_available?

    SolidQueue::Job.distinct.pluck(:queue_name).compact.sort
  rescue ActiveRecord::StatementInvalid
    []
  end

  def self.queue_depth(queue_name)
    return 0 unless solid_queue_available?

    SolidQueue::ReadyExecution.where(queue_name: queue_name).count +
      SolidQueue::ScheduledExecution.where(queue_name: queue_name).count
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.ready_job_count(queue_name)
    return 0 unless solid_queue_available?
    SolidQueue::ReadyExecution.where(queue_name: queue_name).count
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.claimed_job_count(queue_name)
    return 0 unless solid_queue_available?
    SolidQueue::ClaimedExecution.joins(:job).where("solid_queue_jobs.queue_name = ?", queue_name).count
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.scheduled_job_count(queue_name)
    return 0 unless solid_queue_available?
    SolidQueue::ScheduledExecution.where(queue_name: queue_name).count
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.blocked_job_count(queue_name)
    return 0 unless solid_queue_available?
    SolidQueue::BlockedExecution.joins(:job).where("solid_queue_jobs.queue_name = ?", queue_name).count
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.queue_paused?(queue_name)
    return false unless solid_queue_available?
    SolidQueue::Pause.where(queue_name: queue_name).exists?
  rescue ActiveRecord::StatementInvalid
    false
  end

  def self.process_alive?(process, now = Time.current)
    (now - process.last_heartbeat_at) < DEFAULT_WORKER_STALE_WARNING
  end

  def self.process_stale?(process, now = Time.current)
    (now - process.last_heartbeat_at) >= DEFAULT_WORKER_STALE_WARNING
  end

  def self.process_status(process, now = Time.current)
    age = now - process.last_heartbeat_at
    return "critical" if age >= DEFAULT_WORKER_STALE_CRITICAL
    return "stale" if age >= DEFAULT_WORKER_STALE_WARNING
    "healthy"
  end

  def self.stale_claimed_jobs
    return [] unless solid_queue_available?
    threshold = DEFAULT_STALE_JOB_WARNING.ago
    SolidQueue::ClaimedExecution
      .joins(:job)
      .where("solid_queue_claimed_executions.created_at < ?", threshold)
      .includes(:job)
      .map(&:job)
  rescue ActiveRecord::StatementInvalid
    []
  end

  def self.jobs_per_minute
    return 0 unless solid_queue_available?
    completed_last_minute = SolidQueue::Job
                             .where("finished_at >= ?", 1.minute.ago)
                             .count
    completed_last_minute
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.estimated_clearance_time
    return 0 unless solid_queue_available?
    total_pending = SolidQueue::ReadyExecution.count + SolidQueue::ScheduledExecution.count
    rate = jobs_per_minute
    return 0 if rate.zero?
    (total_pending.to_f / rate).round(2)
  rescue ActiveRecord::StatementInvalid
    0
  end

  def self.median(array)
    sorted = array.sort
    len = sorted.length
    (sorted[(len - 1) / 2] + sorted[len / 2]) / 2.0
  end

  def self.percentile(array, percentile)
    sorted = array.sort
    index = (percentile * (sorted.length - 1)).ceil
    sorted[index]
  end
end
