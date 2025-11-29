class ImageProcessingJob < ApplicationJob
  include Monitorable

  queue_as :default

  def perform(inventory_item, additional_image_id = nil)
    if additional_image_id
      # Process additional image
      image = inventory_item.additional_images.find(additional_image_id)
      log_image_info(image, inventory_item, "additional")
      process_image_variants(image)
      strip_exif_data(image)
    else
      # Process primary image
      image = inventory_item.primary_image
      log_image_info(image, inventory_item, "primary")
      process_image_variants(image)
      strip_exif_data(image)
    end
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error "ImageProcessingJob: Image not found - #{e.message}"
  rescue StandardError => e
    Rails.logger.error "ImageProcessingJob: Error processing image - #{e.message}"
    raise e
  end

  private

  def log_image_info(image, inventory_item, image_type)
    return unless image.present?

    begin
      # Check if image has a blob - works for both association proxies and Attachment objects
      blob = image.blob
      return unless blob.present?

      # Log image metadata to help identify images that might trigger VIPS warnings
      # "chunk data is too large" warnings are typically harmless but can indicate
      # images with very large EXIF/metadata or high resolution
      size_mb = blob.byte_size.to_f / (1024 * 1024)
      Rails.logger.info(
        "ImageProcessingJob: Processing #{image_type} image for item #{inventory_item.id} " \
        "(blob_id: #{blob.id}, size: #{size_mb.round(2)}MB, content_type: #{blob.content_type})"
      )
    rescue StandardError => e
      # Don't fail the job if metadata logging fails
      Rails.logger.debug "ImageProcessingJob: Could not log image metadata: #{e.message}"
    end
  end

  def process_image_variants(image)
    return if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

    begin
      # Pre-generate commonly used variants
      image.variant(resize_to_limit: [ 150, 150 ]) # thumb
      image.variant(resize_to_limit: [ 400, 400 ]) # medium
      image.variant(resize_to_limit: [ 800, 800 ]) # large

      Rails.logger.info "ImageProcessingJob: Generated variants for image #{image.id}"
    rescue Vips::Error => e
      # Handle Vips-specific errors (corrupted images, invalid markers, etc.)
      Rails.logger.warn "ImageProcessingJob: Vips error generating variants for image #{image.id}: #{e.message}"
      Rails.logger.debug "ImageProcessingJob: Variants will be generated on-demand if needed"
    rescue StandardError => e
      # Log error but don't fail the job - variants can be generated on-demand
      Rails.logger.warn "ImageProcessingJob: Failed to generate variants for image #{image.id}: #{e.class.name} - #{e.message}"
    end
  end

  def strip_exif_data(image)
    return if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

    begin
      # Use image_processing gem to strip EXIF data
      # This creates a new variant without EXIF metadata for privacy protection
      image.variant(
        loader: { strip: true }, # Strip EXIF and other metadata
        saver: { strip: true }   # Ensure no metadata in output
      ).processed

      Rails.logger.info "ImageProcessingJob: Stripped EXIF data for image #{image.id}"
    rescue Vips::Error => e
      # Handle Vips-specific errors (corrupted images, invalid markers, etc.)
      # These are non-critical - the original image is still usable
      Rails.logger.warn "ImageProcessingJob: Vips error stripping EXIF for image #{image.id}: #{e.message}"
      Rails.logger.debug "ImageProcessingJob: Image may have corrupted metadata but is still usable"
    rescue StandardError => e
      # Log error but don't fail the job - image processing can continue
      # The original image is still available even if EXIF stripping fails
      Rails.logger.warn "ImageProcessingJob: Failed to strip EXIF data for image #{image.id}: #{e.class.name} - #{e.message}"
    end
  end
end
