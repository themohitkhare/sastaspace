class AnalyzeImageForCreationJob < ApplicationJob
  include TrackableJob

  queue_as :default

  # Override concern methods for job-specific configuration
  def self.status_key_prefix
    "inventory_creation_analysis"
  end

  # job_id is the 3rd argument (0-indexed: 2)
  def self.job_id_argument_index
    2
  end

  def perform(image_blob_id, user_id, job_id)
    # Set job_id FIRST so rescue block can update status
    @job_id = job_id
    @image_blob = ActiveStorage::Blob.find(image_blob_id)
    @user = User.find(user_id)

    Rails.logger.info "Starting image analysis for inventory creation (job: #{job_id})"

    # Update status to processing
    update_status("processing", nil, nil)

    # Create analyzer and analyze
    analyzer = Services::InventoryCreationAnalyzer.new(
      image_blob: @image_blob,
      user: @user,
      model_name: "qwen3-vl:8b"
    )

    results = analyzer.analyze

    # Check if analysis failed
    if results["error"].present? || (results["confidence"] || 0) < 0.1
      update_status("failed", nil, { error: results["error"] || "Low confidence analysis" })
      return
    end

    # Success - update status with results (include blob_id for attaching image)
    results_with_blob = results.merge("blob_id" => @image_blob.id)
    update_status("completed", results_with_blob, nil)

    Rails.logger.info "Analysis completed successfully (job: #{job_id})"
  rescue StandardError => e
    Rails.logger.error "Failed to analyze image for creation (job: #{job_id}): #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    update_status("failed", nil, { error: e.message })
    # Don't re-raise - background jobs should gracefully handle errors
  end

  private


  def self.set_status(job_id, status_data)
    key = status_key(job_id)
    status_data["updated_at"] = Time.current.iso8601
    Rails.cache.write(key, status_data.stringify_keys, expires_in: 1.hour)
  end
end
