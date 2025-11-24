class ExtractStockPhotoJob < ApplicationJob
  include TrackableJob

  # Use separate queue for AI-critical jobs to control concurrency
  # This prevents overwhelming ComfyUI with too many simultaneous requests
  queue_as :ai_critical

  # Override concern methods for job-specific configuration
  def self.status_key_prefix
    "stock_photo_extraction"
  end

  # job_id is the 4th argument (0-indexed: 3)
  def self.job_id_argument_index
    3
  end

  def perform(image_blob_id, analysis_results, user_id, job_id, inventory_item_id = nil)
    # Set job_id FIRST so rescue block can update status
    @job_id = job_id
    @image_blob = ActiveStorage::Blob.find(image_blob_id)
    @user = User.find(user_id)
    @analysis_results = analysis_results.is_a?(Hash) ? analysis_results : JSON.parse(analysis_results)
    @inventory_item_id = inventory_item_id  # Store inventory_item_id for precise lookup

    Rails.logger.info "Starting stock photo extraction (job: #{job_id})"

    # Update status to processing
    update_status("processing", nil, nil)
    broadcast_progress("Starting stock photo extraction...")

    # Use stored extraction_prompt if available, otherwise generate it
    extraction_prompt = if @analysis_results["extraction_prompt"].present?
      Rails.logger.info "Using stored extraction_prompt for job #{job_id}"
      @analysis_results["extraction_prompt"]
    else
      # Build extraction prompt from analysis results
      prompt_builder = Services::ExtractionPromptBuilder.new(
        item_data: @analysis_results,
        user: @user
      )
      generated_prompt = prompt_builder.build_prompt
      Rails.logger.info "Generated extraction prompt for job #{job_id}"
      generated_prompt
    end

    # Call ComfyUI for extraction
    Rails.logger.info "Calling ComfyUI for extraction (job: #{job_id})"
    broadcast_progress("Generating stock photo with AI...")

    # Use a longer timeout for extraction (10 minutes) to handle complex generations or queueing
    extraction_timeout = ENV.fetch("COMFY_UI_TIMEOUT", 600).to_i

    extraction_result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: extraction_prompt,
      timeout: extraction_timeout,
      inventory_item_id: @inventory_item_id
    )

    # Log detailed information about the extraction result
    if extraction_result["image_data"].present?
      image_data_size = extraction_result["image_data"].respond_to?(:bytesize) ? extraction_result["image_data"].bytesize : extraction_result["image_data"].size
      Rails.logger.info "ComfyUI extraction result: success=#{extraction_result['success']}, has_image_data=true, image_data_size=#{image_data_size} bytes (#{(image_data_size / 1024.0).round(2)} KB), error=#{extraction_result['error']}"
    else
      Rails.logger.info "ComfyUI extraction result: success=#{extraction_result['success']}, has_image_data=false, error=#{extraction_result['error']}"
    end

    # Check if extraction failed
    if extraction_result["error"].present? || !extraction_result["success"]
      error_msg = extraction_result["error"] || "Extraction failed"
      Rails.logger.error "ComfyUI extraction failed (job: #{job_id}): #{error_msg}"
      update_status("failed", nil, { error: error_msg })
      broadcast_extraction_failed(error_msg)
      return
    end

    # Check if image_data is present
    unless extraction_result["image_data"].present?
      error_msg = "ComfyUI did not return image data"
      Rails.logger.error "ComfyUI extraction succeeded but no image_data returned (job: #{job_id})"
      update_status("failed", nil, { error: error_msg })
      broadcast_extraction_failed(error_msg)
      return
    end

    # Log image_data before passing to create_blob_from_data
    image_data = extraction_result["image_data"]
    image_data_size = image_data.respond_to?(:bytesize) ? image_data.bytesize : image_data.size
    Rails.logger.info "About to create blob from image_data: size=#{image_data_size} bytes (#{(image_data_size / 1024.0).round(2)} KB), type=#{image_data.class}"

    # Validate image_data size - extracted images should be at least 50KB
    if image_data_size < 50_000
      Rails.logger.error "⚠️  CRITICAL: Image data is too small (#{image_data_size} bytes). Expected at least 50KB. This indicates data corruption."
      Rails.logger.error "Attempting to re-download from ComfyUI outputs..."

      # Try to re-download from ComfyUI using outputs
      if extraction_result["outputs"].present?
        begin
          base_uri = URI(ComfyUiService.base_url)
          http = Net::HTTP.new(base_uri.host, base_uri.port)
          http.open_timeout = 10
          http.read_timeout = 30

          # Re-extract image from outputs
          outputs = extraction_result["outputs"]
          re_downloaded = nil

          # Look for SaveImage node output (node "60")
          save_node = outputs["60"]
          if save_node && save_node["images"] && save_node["images"].is_a?(Array) && save_node["images"].any?
            image_info = save_node["images"].first
            filename = image_info["filename"]
            subfolder = image_info["subfolder"] || ""
            type = image_info["type"] || "output"

            view_path = "/view?filename=#{URI.encode_www_form_component(filename)}"
            view_path += "&subfolder=#{URI.encode_www_form_component(subfolder)}" if subfolder.present?
            view_path += "&type=#{URI.encode_www_form_component(type)}"

            request = Net::HTTP::Get.new(view_path)
            response = http.request(request)

            if response.code == "200"
              re_downloaded = response.body
              re_downloaded.force_encoding("BINARY") if re_downloaded.respond_to?(:force_encoding)
              Rails.logger.info "Re-downloaded from ComfyUI: #{re_downloaded.bytesize} bytes"
            end
          end

          if re_downloaded && re_downloaded.bytesize > 50_000
            Rails.logger.info "Successfully re-downloaded: #{re_downloaded.bytesize} bytes (#{(re_downloaded.bytesize / 1024.0).round(2)} KB)"
            image_data = re_downloaded
            image_data_size = re_downloaded.bytesize
          else
            Rails.logger.error "Re-download failed or still too small"
            raise StandardError, "Image data corrupted and re-download failed"
          end
        rescue => e
          Rails.logger.error "Failed to re-download: #{e.message}"
          Rails.logger.error e.backtrace.first(5).join("\n")
          raise StandardError, "Image data is corrupted (#{image_data_size} bytes) and cannot be recovered: #{e.message}"
        end
      else
        raise StandardError, "Image data is corrupted (#{image_data_size} bytes) and cannot be recovered (no outputs for re-download)"
      end
    end

    # Store extracted image as ActiveStorage blob
    Rails.logger.info "Creating blob from extracted image data (job: #{job_id})"
    broadcast_progress("Processing extracted image...")
    extracted_blob = create_blob_from_data(image_data)
    Rails.logger.info "Created extracted blob #{extracted_blob.id} with filename #{extracted_blob.filename} (#{extracted_blob.byte_size} bytes)"

      # Find the inventory item that owns the original image
      # If inventory_item_id is provided, use it directly for precise lookup
      if @inventory_item_id.present?
        Rails.logger.info "Using provided inventory_item_id #{@inventory_item_id} for blob #{@image_blob.id} (job: #{job_id})"
        inventory_item = @user.inventory_items.find_by(id: @inventory_item_id)
        unless inventory_item
          Rails.logger.error "Inventory item #{@inventory_item_id} not found for user #{@user.id}"
          inventory_item = nil
        else
          # Verify the item actually has this blob as primary_image
          unless inventory_item.primary_image.attached? && inventory_item.primary_image.blob.id == @image_blob.id
            Rails.logger.warn "Inventory item #{@inventory_item_id} does not have blob #{@image_blob.id} as primary_image. Will attach result to additional_images."
          else
            Rails.logger.info "Verified inventory item #{@inventory_item_id} has blob #{@image_blob.id} as primary_image"
          end
        end
      else
        Rails.logger.info "Searching for inventory item with primary_image blob #{@image_blob.id} (job: #{job_id})"
        inventory_item = find_inventory_item_for_blob(@image_blob.id)
      end
    original_primary_blob = nil

    if inventory_item
      Rails.logger.info "Found inventory item #{inventory_item.id} for blob #{@image_blob.id} (job: #{job_id})"
      begin
        # Reload to ensure we have the latest state
        inventory_item.reload

        # Check if primary image is still the expected one
        primary_image_matches = inventory_item.primary_image.attached? && inventory_item.primary_image.blob.id == @image_blob.id

        if primary_image_matches
          # Move current primary image to additional_images if it exists
          if inventory_item.primary_image.attached?
            original_primary_blob = inventory_item.primary_image.blob
            Rails.logger.info "Moving original primary image (blob #{original_primary_blob.id}) to additional_images for item #{inventory_item.id}"

            # Detach the primary image (but don't purge the blob - we want to reuse it)
            # Use detach instead of delete to properly remove the association
            inventory_item.primary_image.detach

            # Reload to ensure the attachment is removed
            inventory_item.reload

            # Verify it's detached
            if inventory_item.primary_image.attached?
              Rails.logger.error "Failed to detach primary image from item #{inventory_item.id}"
              raise "Failed to detach primary image"
            end

            # Now attach the original primary image blob to additional_images
            inventory_item.additional_images.attach(original_primary_blob)
            inventory_item.reload

            # Verify it was added to additional_images
            if inventory_item.additional_images.attached? && inventory_item.additional_images.any? { |img| img.blob.id == original_primary_blob.id }
              Rails.logger.info "Moved original primary image to additional_images (blob #{original_primary_blob.id})"
            else
              Rails.logger.warn "Original primary image may not have been added to additional_images"
            end
          end

          # Replace primary image with extracted image
          Rails.logger.info "Replacing primary image with extracted image (blob #{extracted_blob.id}) for item #{inventory_item.id}"

          # Ensure primary_image is not attached (should already be detached if we moved it above)
          if inventory_item.primary_image.attached?
            Rails.logger.warn "Primary image still attached after move operation, detaching now"
            inventory_item.primary_image.detach
            inventory_item.reload
          end

          # Attach the new extracted blob
          inventory_item.primary_image.attach(extracted_blob)
          Rails.logger.info "Called attach for blob #{extracted_blob.id} on inventory item #{inventory_item.id}"
        else
          # Primary image changed - attach to additional_images instead
          Rails.logger.warn "Primary image changed since job started (expected blob #{@image_blob.id}). Attaching extracted image to additional_images instead."
          inventory_item.additional_images.attach(extracted_blob)
          Rails.logger.info "Attached extracted image (blob #{extracted_blob.id}) to additional_images for item #{inventory_item.id}"
        end

        # Force save and reload to ensure attachment is persisted
        inventory_item.save! if inventory_item.changed?
        inventory_item.reload

        if primary_image_matches
          # Double-check the attachment was created
          attachment = ActiveStorage::Attachment.find_by(
            record_type: "InventoryItem",
            record_id: inventory_item.id,
            name: "primary_image",
            blob_id: extracted_blob.id
          )

          if attachment
            Rails.logger.info "Attachment record confirmed: attachment #{attachment.id} links blob #{extracted_blob.id} to item #{inventory_item.id}"
          else
            Rails.logger.error "Attachment record NOT found in database after attach call!"
          end

          # Verify the attachment succeeded
          if inventory_item.primary_image.attached?
            attached_blob_id = inventory_item.primary_image.blob.id
            if attached_blob_id == extracted_blob.id
              Rails.logger.info "Successfully replaced primary image with extracted image (blob #{extracted_blob.id}) for inventory item #{inventory_item.id}"
            else
              Rails.logger.error "Primary image attachment verification failed: expected blob #{extracted_blob.id}, got #{attached_blob_id} for item #{inventory_item.id}"
              raise "Primary image attachment verification failed: expected blob #{extracted_blob.id}, got #{attached_blob_id}"
            end
          else
            Rails.logger.error "Primary image attachment verification failed: no attachment found for item #{inventory_item.id}"
            raise "Primary image attachment verification failed: no attachment found"
          end
        else
           # Verify attached to additional
           if inventory_item.additional_images.attached? && inventory_item.additional_images.any? { |img| img.blob.id == extracted_blob.id }
             Rails.logger.info "Successfully attached extracted image (blob #{extracted_blob.id}) to additional_images"
           else
             Rails.logger.error "Failed to attach extracted image to additional_images"
           end
        end
      rescue StandardError => e
        Rails.logger.error "Failed to replace primary image with extracted image: #{e.message}"
        Rails.logger.error e.backtrace.join("\n")
        # Don't fail the job - image is still created and accessible via blob_id
      end
    else
      Rails.logger.warn "Could not find inventory item for blob #{@image_blob.id} - extracted image not attached"
    end

    # Check if image was actually replaced
    primary_image_replaced = inventory_item&.primary_image&.attached? && inventory_item.primary_image.blob.id == extracted_blob.id

    # Update status with success
    completion_data = {
      "original_blob_id" => @image_blob.id,
      "extracted_blob_id" => extracted_blob.id,
      "extraction_prompt" => extraction_prompt,
      "comfyui_job_id" => extraction_result["job_id"],
      "inventory_item_id" => inventory_item&.id,
      "primary_image_replaced" => primary_image_replaced,
      "original_moved_to_additional" => original_primary_blob.present?
    }
    update_status("completed", completion_data, nil)
    broadcast_extraction_complete(completion_data)

    # Only mark that extraction has completed successfully if the image was actually replaced
    if inventory_item && primary_image_replaced
      inventory_item.update_column(:stock_photo_extraction_completed_at, Time.current)
      Rails.logger.info "Marked inventory item #{inventory_item.id} as having completed stock photo extraction"
    elsif inventory_item
      Rails.logger.warn "Extraction completed but image was not replaced for inventory item #{inventory_item.id} - not marking as completed"
    end

    Rails.logger.info "Extraction completed successfully (job: #{job_id})"
  rescue StandardError => e
    Rails.logger.error "Failed to extract stock photo (job: #{job_id}): #{e.message}"
    Rails.logger.error e.backtrace.join("\n")
    update_status("failed", nil, { error: e.message })
    broadcast_extraction_failed(e.message) if @user&.id
    # Don't re-raise - background jobs should gracefully handle errors
  end

  private

  def create_blob_from_data(image_data)
    # Convert ComfyUI output to ActiveStorage blob
    # image_data can be:
    # 1. Base64 encoded string
    # 2. File path (if ComfyUI returns local path)
    # 3. Binary data (String with binary encoding)

    Rails.logger.info "create_blob_from_data: Input data type=#{image_data.class}, size=#{image_data.respond_to?(:bytesize) ? image_data.bytesize : 'unknown'} bytes"

    decoded_data = if image_data.is_a?(String)
      # Check if it's a file path first (short paths are unlikely to be base64)
      if image_data.length < 100 && File.exist?(image_data)
        Rails.logger.info "Reading image from file path: #{image_data}"
        file_data = File.binread(image_data)
        Rails.logger.info "Read #{file_data.bytesize} bytes from file"
        file_data
      else
        # CRITICAL: Check PNG header FIRST before trying base64 decode
        # Binary PNG data starts with: 89 50 4E 47 0D 0A 1A 0A
        # If it's already binary PNG, don't try to decode as base64
        if image_data.bytesize >= 8
          png_header = image_data[0..7].bytes
          is_png = png_header == [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]

          if is_png
            Rails.logger.info "Detected PNG header - treating as binary image data: #{image_data.bytesize} bytes"
            image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
            image_data
          else
            # No PNG header - might be base64 encoded
            # Base64 strings are typically longer and contain only base64 characters
            # Check if string looks like base64 (contains only base64 chars and is longer)
            base64_pattern = /\A[A-Za-z0-9+\/]*={0,2}\z/
            looks_like_base64 = image_data.length > 100 && image_data.match?(base64_pattern) && !image_data.include?("\x00")

            if looks_like_base64
              begin
                decoded = Base64.decode64(image_data)
                # Validate decoded data has PNG header
                if decoded.bytesize >= 8
                  decoded_png_header = decoded[0..7].bytes
                  if decoded_png_header == [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]
                    Rails.logger.info "Decoded base64 image data (valid PNG): #{image_data.bytesize} bytes -> #{decoded.bytesize} bytes"
                    decoded
                  else
                    Rails.logger.warn "Base64 decode produced invalid PNG - treating original as binary"
                    image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
                    image_data
                  end
                else
                  Rails.logger.warn "Base64 decode produced data too small - treating original as binary"
                  image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
                  image_data
                end
              rescue ArgumentError
                Rails.logger.info "Not valid base64, treating as binary image data: #{image_data.bytesize} bytes"
                image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
                image_data
              end
            else
              # Doesn't look like base64, treat as binary
              Rails.logger.info "Treating as binary image data: #{image_data.bytesize} bytes"
              image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
              image_data
            end
          end
        else
          # Too small to check, treat as binary
          Rails.logger.info "Data too small to check, treating as binary: #{image_data.bytesize} bytes"
          image_data.force_encoding("BINARY") if image_data.respond_to?(:force_encoding)
          image_data
        end
      end
    else
      image_data
    end

    # Validate that we have actual data
    if decoded_data.nil? || decoded_data.empty?
      raise StandardError, "No image data received from ComfyUI"
    end

    decoded_size = decoded_data.respond_to?(:bytesize) ? decoded_data.bytesize : decoded_data.size
    Rails.logger.info "Decoded data size: #{decoded_size} bytes"

    # Validate minimum size (PNG header is at least 8 bytes)
    if decoded_size < 8
      raise StandardError, "Image data too small (#{decoded_size} bytes) - likely corrupted"
    end

    # Warn if image is suspiciously small (less than 10KB is likely corrupted)
    if decoded_size < 10_240
      Rails.logger.error "⚠️  WARNING: Image data is suspiciously small (#{decoded_size} bytes / #{decoded_size / 1024.0} KB). Expected at least 100KB for extracted images."
    end

    # Validate PNG header (PNG files start with: 89 50 4E 47 0D 0A 1A 0A)
    png_header = decoded_data[0..7].bytes
    is_png = png_header == [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]

    if is_png
      Rails.logger.info "Valid PNG header detected"
    else
      Rails.logger.warn "PNG header validation failed (first 8 bytes: #{png_header.inspect}), but continuing anyway"
    end

    # Create StringIO with binary encoding
    string_io = StringIO.new(decoded_data)
    string_io.set_encoding("BINARY")

    Rails.logger.info "Creating ActiveStorage blob from #{decoded_size} bytes of image data"

    # Create ActiveStorage blob
    blob = ActiveStorage::Blob.create_and_upload!(
      io: string_io,
      filename: "extracted_#{@image_blob.filename.base}_#{SecureRandom.hex(4)}.png",
      content_type: "image/png"
    )

    Rails.logger.info "Created blob #{blob.id} with #{blob.byte_size} bytes"

    # Validate blob size matches input data size
    if blob.byte_size != decoded_size
      Rails.logger.error "⚠️  WARNING: Blob size mismatch! Input: #{decoded_size} bytes, Blob: #{blob.byte_size} bytes (difference: #{decoded_size - blob.byte_size} bytes)"
    else
      Rails.logger.info "✓ Blob size matches input data size: #{blob.byte_size} bytes"
    end

    blob
  end

  def find_inventory_item_for_blob(blob_id)
    # Find inventory item that has this blob as primary image
    # Try multiple approaches to find the item

    # Method 1: Direct join query (most efficient)
    item = InventoryItem.joins(:primary_image_attachment)
      .where(active_storage_attachments: { blob_id: blob_id, name: "primary_image" })
      .where(user_id: @user.id) # Scope to current user for security
      .first

    if item
      Rails.logger.info "Found inventory item #{item.id} via join query for blob #{blob_id}"
      return item
    end

    # Method 2: Find via ActiveStorage::Attachment directly
    attachment = ActiveStorage::Attachment.find_by(
      blob_id: blob_id,
      name: "primary_image",
      record_type: "InventoryItem"
    )
    if attachment
      item = InventoryItem.find_by(id: attachment.record_id, user_id: @user.id)
      if item
        Rails.logger.info "Found inventory item #{item.id} via attachment lookup for blob #{blob_id}"
        return item
      end
    end

    # Method 3: Search user's inventory items and check their primary_image
    # This is a fallback but scoped to user for better performance
    Rails.logger.warn "Trying fallback method to find inventory item for blob #{blob_id} (user #{@user.id})"
    @user.inventory_items.find_each do |inv_item|
      if inv_item.primary_image.attached? && inv_item.primary_image.blob.id == blob_id
        Rails.logger.info "Found inventory item #{inv_item.id} via fallback search for blob #{blob_id}"
        return inv_item
      end
    end

    # Method 4: Check if blob is attached to any association (primary or additional)
    # Sometimes the blob might be in additional_images
    Rails.logger.warn "Checking if blob #{blob_id} is in additional_images for user #{@user.id}"
    attachment = ActiveStorage::Attachment.find_by(
      blob_id: blob_id,
      record_type: "InventoryItem"
    )
    if attachment
      item = InventoryItem.find_by(id: attachment.record_id, user_id: @user.id)
      if item
        Rails.logger.info "Found inventory item #{item.id} with blob #{blob_id} attached as '#{attachment.name}'"
        return item
      end
    end

    Rails.logger.error "Could not find inventory item for blob #{blob_id} using any method (user #{@user.id})"
    nil
  end

  private

  def broadcast_progress(message)
    return unless @user&.id

    ActionCable.server.broadcast(
      "stock_extraction_#{@user.id}",
      {
        type: "extraction_progress",
        message: message,
        job_id: @job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_extraction_complete(data)
    return unless @user&.id

    ActionCable.server.broadcast(
      "stock_extraction_#{@user.id}",
      {
        type: "extraction_complete",
        job_id: @job_id,
        data: data,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_extraction_failed(error_message)
    return unless @user&.id

    ActionCable.server.broadcast(
      "stock_extraction_#{@user.id}",
      {
        type: "extraction_failed",
        job_id: @job_id,
        error: error_message,
        timestamp: Time.current.iso8601
      }
    )
  end
end
