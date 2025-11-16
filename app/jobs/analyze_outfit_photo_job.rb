class AnalyzeOutfitPhotoJob < ApplicationJob
  include TrackableJob

  queue_as :default

  # Override concern methods for job-specific configuration
  def self.status_key_prefix
    "outfit_photo_analysis"
  end

  # job_id is the 3rd argument (0-indexed: 2)
  def self.job_id_argument_index
    2
  end

  def perform(image_blob_id, user_id, job_id)
    @job_id = job_id  # Assign @job_id first so it's available in rescue block

    @image_blob = ActiveStorage::Blob.find(image_blob_id)
    @user = User.find(user_id)

    Rails.logger.info "Starting outfit photo analysis (job: #{job_id})"

    # Update status to processing
    update_status("processing", nil, nil)

    # Create analyzer and analyze
    analyzer = Services::OutfitPhotoAnalyzer.new(
      image_blob: @image_blob,
      user: @user,
      model_name: "qwen3-vl:8b"
    )

    results = analyzer.analyze

    # Check if analysis failed
    if results["error"].present? || (results["total_items"] || 0) == 0
      error_msg = results["error"] || "No items detected in outfit photo"
      update_status("failed", nil, { error: error_msg })
      return
    end

    # Success - update status with results (include blob_id for attaching image to items)
    results_with_blob = results.merge("blob_id" => @image_blob.id)
    update_status("completed", results_with_blob, nil)

    Rails.logger.info "Outfit photo analysis completed successfully (job: #{job_id}). Detected #{results['total_items']} items."
  rescue StandardError => e
    Rails.logger.error "Failed to analyze outfit photo (job: #{job_id}): #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    update_status("failed", nil, { error: e.message })
    # Don't re-raise - background jobs should gracefully handle errors
  end

  private
end
