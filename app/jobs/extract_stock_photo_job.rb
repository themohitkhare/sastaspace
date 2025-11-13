class ExtractStockPhotoJob < ApplicationJob
  queue_as :default

  # Store job status and results in Rails cache
  def self.status_key(job_id)
    "stock_photo_extraction:#{job_id}"
  end

  def perform(image_blob_id, analysis_results, user_id, job_id)
    # Set job_id FIRST so rescue block can update status
    @job_id = job_id
    @image_blob = ActiveStorage::Blob.find(image_blob_id)
    @user = User.find(user_id)
    @analysis_results = analysis_results.is_a?(Hash) ? analysis_results : JSON.parse(analysis_results)

    Rails.logger.info "Starting stock photo extraction (job: #{job_id})"

    # Update status to processing
    update_status("processing", nil, nil)

    # Build extraction prompt from analysis results
    prompt_builder = Services::ExtractionPromptBuilder.new(
      item_data: @analysis_results,
      user: @user
    )

    extraction_prompt = prompt_builder.build_prompt

    Rails.logger.info "Generated extraction prompt for job #{job_id}"

    # Call ComfyUI for extraction
    extraction_result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: extraction_prompt
    )

    # Check if extraction failed
    if extraction_result["error"].present? || !extraction_result["success"]
      error_msg = extraction_result["error"] || "Extraction failed"
      update_status("failed", nil, { error: error_msg })
      return
    end

    # Store extracted image as ActiveStorage blob
    extracted_blob = create_blob_from_data(extraction_result["image_data"])

    # Update status with success
    update_status("completed", {
      "original_blob_id" => @image_blob.id,
      "extracted_blob_id" => extracted_blob.id,
      "extraction_prompt" => extraction_prompt,
      "comfyui_job_id" => extraction_result["job_id"]
    }, nil)

    Rails.logger.info "Extraction completed successfully (job: #{job_id})"
  rescue StandardError => e
    Rails.logger.error "Failed to extract stock photo (job: #{job_id}): #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    update_status("failed", nil, { error: e.message })
    # Don't re-raise - background jobs should gracefully handle errors
  end

  private

  def update_status(status, data, error)
    status_data = {
      "status" => status,
      "data" => data,
      "error" => error,
      "updated_at" => Time.current.iso8601
    }

    # Store in Rails cache
    Rails.cache.write(self.class.status_key(@job_id), status_data, expires_in: 1.hour)
  end

  def create_blob_from_data(image_data)
    # Convert ComfyUI output to ActiveStorage blob
    # image_data can be:
    # 1. Base64 encoded string
    # 2. File path (if ComfyUI returns local path)
    # 3. Binary data

    decoded_data = if image_data.is_a?(String)
      # Try to decode as base64 first
      begin
        Base64.decode64(image_data)
      rescue ArgumentError
        # If not base64, treat as file path
        if File.exist?(image_data)
          File.binread(image_data)
        else
          # Assume it's already binary data
          image_data
        end
      end
    else
      image_data
    end

    # Create ActiveStorage blob
    ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new(decoded_data),
      filename: "extracted_#{@image_blob.filename.base}_#{SecureRandom.hex(4)}.png",
      content_type: "image/png"
    )
  end

  def self.get_status(job_id)
    key = status_key(job_id)
    Rails.cache.read(key) || {
      "status" => "not_found",
      "data" => nil,
      "error" => { "message" => "Job not found" },
      "updated_at" => Time.current.iso8601
    }
  end
end
