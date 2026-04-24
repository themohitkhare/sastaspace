# frozen_string_literal: true

class IngestController < ApplicationController
  MAX_IMAGES    = 20
  MAX_BYTES     = 8 * 1024 * 1024  # 8 MB per image
  ALLOWED_TYPES = %w[image/jpeg image/png image/webp image/gif].freeze

  def new
    # GET /almirah/onboarding — ERB file picker form.
  end

  def create
    # POST /almirah/ingest/start — accept bulk upload, enqueue one background
    # job per image, redirect to the job polling page.
    files = params[:images]

    if files.blank?
      return redirect_to onboarding_path, alert: "Please select at least one image."
    end

    files = Array(files)

    if files.size > MAX_IMAGES
      return redirect_to onboarding_path, alert: "Upload at most #{MAX_IMAGES} images at once."
    end

    invalid = files.reject { |f| ALLOWED_TYPES.include?(f.content_type) }
    if invalid.any?
      types = invalid.map(&:content_type).uniq.join(", ")
      return redirect_to onboarding_path, alert: "Unsupported file type(s): #{types}. JPEG/PNG/WebP/GIF only."
    end

    too_large = files.select { |f| f.size > MAX_BYTES }
    if too_large.any?
      return redirect_to onboarding_path, alert: "#{too_large.size} file(s) exceed the 8 MB limit."
    end

    # Create one IngestJob record per batch, enqueue a Solid Queue job per file.
    job_record = IngestJob.create!(
      user_id:     current_user.id,
      photo_count: files.size,
      status:      "queued"
    )

    files.each do |file|
      image_data = Base64.strict_encode64(file.read)
      media_type = file.content_type
      AlmirahIngestJob.perform_later(
        job_record.id.to_s,
        current_user.id,
        image_data,
        media_type
      )
    end

    redirect_to ingest_job_path(job_id: job_record.id)
  end

  def show
    @job = IngestJob.find(params[:job_id])
    # Simple poll page — Turbo-driven auto-refresh every 2s while processing.
    respond_to do |format|
      format.html
      format.json { render json: { status: @job.status, photo_count: @job.photo_count } }
    end
  rescue ActiveRecord::RecordNotFound
    redirect_to onboarding_path, alert: "Job not found."
  end
end
