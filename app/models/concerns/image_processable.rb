# Concern for image processing functionality
module ImageProcessable
  extend ActiveSupport::Concern

  included do
    # Security: Strip EXIF data and process images
    after_create_commit :process_images
    after_update_commit :process_images

    # Image validations
    validate :validate_primary_image_content_type
    validate :validate_primary_image_size
    validate :validate_additional_images_content_type
    validate :validate_additional_images_size
  end

  # Image variants for different use cases
  def primary_image_variants
    return {} unless primary_image.attached?

    {
      thumb: primary_image.variant(resize_to_limit: [ 150, 150 ]),
      medium: primary_image.variant(resize_to_limit: [ 400, 400 ]),
      large: primary_image.variant(resize_to_limit: [ 800, 800 ])
    }
  end

  def additional_image_variants(image)
    return {} if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

    {
      thumb: image.variant(resize_to_limit: [ 150, 150 ]),
      medium: image.variant(resize_to_limit: [ 400, 400 ]),
      large: image.variant(resize_to_limit: [ 800, 800 ])
    }
  end

  private

  def process_images
    if primary_image.attached?
      ImageProcessingJob.perform_later(self)
    end
    additional_images.each do |image|
      if image.present?
        ImageProcessingJob.perform_later(self, image.id)
      end
    end
  end

  def validate_primary_image_content_type
    return unless primary_image.attached?

    allowed_types = %w[image/jpeg image/jpg image/png image/webp]
    unless allowed_types.include?(primary_image.content_type)
      errors.add(:primary_image, "is not a valid content type")
    end
  end

  def validate_primary_image_size
    return unless primary_image.attached?

    max_size = 5.megabytes
    if primary_image.byte_size > max_size
      errors.add(:primary_image, "is too large")
    end
  end

  def validate_additional_images_content_type
    return unless additional_images.attached?

    allowed_types = %w[image/jpeg image/jpg image/png image/webp]
    additional_images.each do |image|
      unless allowed_types.include?(image.content_type)
        errors.add(:additional_images, "is not a valid content type")
        break
      end
    end
  end

  def validate_additional_images_size
    return unless additional_images.attached?

    max_size = 5.megabytes
    additional_images.each do |image|
      if image.byte_size > max_size
        errors.add(:additional_images, "is too large")
        break
      end
    end
  end
end
