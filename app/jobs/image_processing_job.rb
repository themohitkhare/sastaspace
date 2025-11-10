class ImageProcessingJob < ApplicationJob
  include Monitorable

  queue_as :default

  def perform(inventory_item, additional_image_id = nil)
    if additional_image_id
      # Process additional image
      image = inventory_item.additional_images.find(additional_image_id)
      process_image_variants(image)
      strip_exif_data(image)
    else
      # Process primary image
      process_image_variants(inventory_item.primary_image)
      strip_exif_data(inventory_item.primary_image)
    end
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error "ImageProcessingJob: Image not found - #{e.message}"
  rescue StandardError => e
    Rails.logger.error "ImageProcessingJob: Error processing image - #{e.message}"
    raise e
  end

  private

  def process_image_variants(image)
    return if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

    # Pre-generate commonly used variants
    image.variant(resize_to_limit: [ 150, 150 ]) # thumb
    image.variant(resize_to_limit: [ 400, 400 ]) # medium
    image.variant(resize_to_limit: [ 800, 800 ]) # large

    Rails.logger.info "ImageProcessingJob: Generated variants for image #{image.id}"
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
    rescue StandardError => e
      # Log error but don't fail the job - image processing can continue
      Rails.logger.warn "ImageProcessingJob: Failed to strip EXIF data for image #{image.id}: #{e.message}"
    end
  end
end
