#!/usr/bin/env ruby
# Quick verification script for TrackableJob concern
# Run with: bundle exec rails runner test/jobs/concerns/verify_trackable_job.rb

class TestJob < ApplicationJob
  include TrackableJob

  def self.status_key_prefix
    "test_job"
  end

  def self.job_id_argument_index
    0  # job_id is first argument
  end

  def perform(job_id)
    @job_id = job_id
    update_status("completed", { "result" => "success" }, nil)
  end
end

puts "Testing TrackableJob concern..."
puts "=" * 50

# Test 1: Status key generation
job_id = "test-123"
status_key = TestJob.status_key(job_id)
active_job_id_key = TestJob.active_job_id_key(job_id)
puts "✓ Status key: #{status_key}"
puts "✓ ActiveJob ID key: #{active_job_id_key}"

# Test 2: Enqueue and check mapping
puts "\nEnqueuing job..."
job = TestJob.perform_later(job_id)
puts "✓ Job enqueued with ID: #{job.job_id}"

# Wait for after_enqueue callback
sleep 0.2

# Check if mapping was stored
stored_active_job_id = Rails.cache.read(active_job_id_key)
if stored_active_job_id.present?
  puts "✓ ActiveJob ID mapping stored: #{stored_active_job_id}"
  if stored_active_job_id == job.job_id
    puts "✓ Mapping matches job ID!"
  else
    puts "✗ Mapping mismatch! Expected: #{job.job_id}, Got: #{stored_active_job_id}"
  end
else
  puts "✗ ActiveJob ID mapping NOT stored!"
  puts "  This means after_enqueue callback may not be working correctly"
end

# Test 3: Status update
puts "\nPerforming job..."
TestJob.perform_now(job_id)

# Check status
status = TestJob.get_status(job_id)
if status["status"] == "completed"
  puts "✓ Status updated correctly: #{status['status']}"
else
  puts "✗ Status update failed: #{status.inspect}"
end

# Test 4: Recovery (if SolidQueue available)
if defined?(SolidQueue::Job)
  puts "\nTesting recovery mechanism..."
  # Clear status cache
  Rails.cache.delete(status_key)

  # Try to recover
  recovered_status = TestJob.send(:recover_status_from_queue, job_id)
  if recovered_status
    puts "✓ Recovery successful: #{recovered_status['status']}"
  else
    puts "⚠ Recovery returned nil (job may not be in SolidQueue yet)"
  end
else
  puts "\n⚠ SolidQueue not available - skipping recovery test"
end

puts "\n" + "=" * 50
puts "Verification complete!"
