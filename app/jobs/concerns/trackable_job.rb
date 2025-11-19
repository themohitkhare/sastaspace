# Concern for jobs that need status tracking and recovery
# Provides methods for tracking job status in cache and recovering from Sidekiq
# after server restarts or cache expiry.
#
# Usage:
#   class MyJob < ApplicationJob
#     include TrackableJob
#
#     # Override to provide job-specific cache key prefix
#     def self.status_key_prefix
#       "my_job"
#     end
#
#     # Override to specify which argument index contains the custom job_id
#     # Default is -1 (last argument)
#     def self.job_id_argument_index
#       2  # job_id is the 3rd argument (0-indexed)
#     end
#
#     def perform(arg1, arg2, job_id)
#       update_status("processing", nil, nil)
#       # ... job logic ...
#       update_status("completed", result_data, nil)
#     end
#   end
module TrackableJob
  extend ActiveSupport::Concern

  included do
    # Store mapping when job is enqueued (after it's enqueued, job_id is available)
    after_enqueue :store_job_mapping
  end

  # Class methods that can be overridden by including classes
  module ClassMethods
    # Generate cache key for job status
    # Override in including class to provide job-specific prefix
    def status_key(job_id)
      "#{status_key_prefix}:#{job_id}"
    end

    # Cache key prefix for this job type
    # Override in including class
    def status_key_prefix
      # Default to underscored class name
      name.underscore.gsub("/", "_")
    end

    # Generate cache key for ActiveJob ID mapping
    def active_job_id_key(job_id)
      "#{status_key_prefix}:active_job_id:#{job_id}"
    end

    # Argument index that contains the custom job_id
    # Override in including class if job_id is not the last argument
    # Returns -1 by default (last argument)
    def job_id_argument_index
      -1
    end

    # Get job status from cache or recover from Solid Queue
    def get_status(job_id)
      key = status_key(job_id)
      cached_status = Rails.cache.read(key)

      # If status is in cache, return it
      if cached_status.present?
        # If it's a hash, ensure string keys for consistency
        # If it's not a hash (e.g., string), return as-is (for backward compatibility)
        return cached_status.is_a?(Hash) ? cached_status.stringify_keys : cached_status
      end

      # Cache miss - try to recover from Solid Queue
      recovered_status = recover_status_from_queue(job_id)
      return recovered_status if recovered_status.present?

      # No status found in cache or queue
      {
        "status" => "not_found",
        "data" => nil,
        "error" => { "message" => "Job not found or expired. If the job was recently queued, it may still be processing." },
        "updated_at" => Time.current.iso8601
      }
    rescue StandardError => e
      Rails.logger.error "Error reading job status for #{name}: #{e.message}"
      { "status" => "error", "error" => "Could not retrieve job status" }
    end

    # Recover job status from Sidekiq when cache is missing
    # This handles cases where:
    # - Server restarted and cache was cleared
    # - Cache expired but job is still in queue
    # - Job is processing but status wasn't updated yet
    def recover_status_from_queue(job_id)
      return nil unless defined?(Sidekiq)

      begin
        active_job_id = Rails.cache.read(active_job_id_key(job_id))
        return nil unless active_job_id.present?

        # Use Sidekiq API to find job status
        # Sidekiq stores jobs in Redis, so we need to check different queues
        status = recover_from_sidekiq(active_job_id)
        return nil unless status

        # Re-cache the recovered status (with shorter expiry since it's incomplete)
        Rails.cache.write(status_key(job_id), status, expires_in: 15.minutes)
        status
      rescue StandardError => e
        Rails.logger.warn "Failed to recover job status from Sidekiq for #{name} job_id #{job_id}: #{e.message}"
        nil
      end
    end

    # Recover job status from Sidekiq using Sidekiq API
    def recover_from_sidekiq(active_job_id)
      # Check if job is in scheduled queue
      scheduled = Sidekiq::ScheduledSet.new
      job = scheduled.find { |j| j.jid == active_job_id }
      if job
        return {
          "status" => "scheduled",
          "data" => nil,
          "error" => nil,
          "updated_at" => Time.at(job.score).iso8601,
          "recovered" => true,
          "note" => "Job is scheduled to run"
        }
      end

      # Check if job is in retry queue
      retries = Sidekiq::RetrySet.new
      job = retries.find { |j| j.jid == active_job_id }
      if job
        return {
          "status" => "retrying",
          "data" => nil,
          "error" => { "message" => job.item["error_message"] || "Job is retrying" },
          "updated_at" => Time.at(job.score).iso8601,
          "recovered" => true,
          "note" => "Job is retrying after failure"
        }
      end

      # Check if job is in dead queue
      dead = Sidekiq::DeadSet.new
      job = dead.find { |j| j.jid == active_job_id }
      if job
        return {
          "status" => "failed",
          "data" => nil,
          "error" => { "message" => job.item["error_message"] || "Job failed" },
          "updated_at" => Time.at(job.score).iso8601,
          "recovered" => true,
          "note" => "Job has failed and is in dead queue"
        }
      end

      # Job might be processing or completed (not in any queue)
      # We can't determine exact status without additional tracking
      nil
    end

    private
  end

  # Instance methods
  private

  # Store mapping from custom job_id to ActiveJob ID when job is enqueued
  def store_job_mapping
    # Extract custom job_id from arguments
    job_id_index = self.class.job_id_argument_index
    custom_job_id = if job_id_index == -1
      arguments.last
    elsif arguments.length > job_id_index
      arguments[job_id_index]
    end

    # After enqueue, job_id should be available on self
    # Note: In test mode with inline adapter, job_id might not be set yet
    # In production with Sidekiq, job_id will be available
    active_job_id = if respond_to?(:job_id) && job_id.present?
      job_id
    elsif respond_to?(:provider_job_id) && provider_job_id.present?
      provider_job_id
    end

    if custom_job_id.present? && active_job_id
      Rails.cache.write(
        self.class.active_job_id_key(custom_job_id),
        active_job_id,
        expires_in: 24.hours # Keep mapping longer than status cache
      )
      Rails.logger.debug "Stored job mapping for #{self.class.name}: custom_job_id=#{custom_job_id} -> active_job_id=#{active_job_id}"
    end
  end

  # Update job status in cache
  # Override @job_id in perform method before calling this
  def update_status(status, data, error)
    # Check if @job_id is defined and has a non-nil, non-empty value
    # First check if variable is defined, then check if it has a value
    unless instance_variable_defined?(:@job_id)
      raise "@job_id must be set before calling update_status"
    end

    job_id_value = instance_variable_get(:@job_id)
    if job_id_value.blank?
      raise "@job_id must be set before calling update_status"
    end

    status_data = {
      "status" => status,
      "data" => data,
      "error" => error,
      "updated_at" => Time.current.iso8601
    }

    # Store in Rails cache (use job_id_value to avoid accessing @job_id again)
    Rails.cache.write(self.class.status_key(job_id_value), status_data, expires_in: 1.hour)
  end
end
