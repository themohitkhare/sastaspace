# Service object for queueing stock photo extraction jobs
# Handles validation, parameter sanitization, and job enqueueing
# Can be called from controllers or other jobs
class StockPhotoExtractionService
  attr_reader :image_blob, :user, :analysis_results, :inventory_item_id

  def initialize(image_blob:, user:, analysis_results:, inventory_item_id: nil)
    @image_blob = image_blob
    @user = user
    @analysis_results = sanitize_analysis_results(analysis_results)
    @inventory_item_id = inventory_item_id
  end

  # Queue the extraction job
  # Returns the job_id if successful, raises error if validation fails
  def queue_extraction
    validate!

    job_id = SecureRandom.uuid

    ExtractStockPhotoJob.perform_later(
      image_blob.id,
      @analysis_results,
      user.id,
      job_id,
      inventory_item_id
    )

    Rails.logger.info "Stock photo extraction job queued. Blob ID: #{image_blob.id}, Inventory Item ID: #{inventory_item_id || 'auto-detect'}, Job ID: #{job_id}, User: #{user.id}"

    job_id
  end

  private

  def validate!
    raise ArgumentError, "Image blob is required" unless image_blob.present?
    raise ArgumentError, "User is required" unless user.present?
    raise ArgumentError, "Analysis results are required" unless @analysis_results.present?

    # Validate blob exists
    unless image_blob.is_a?(ActiveStorage::Blob)
      raise ArgumentError, "Invalid image blob"
    end

    # Validate gender appropriateness
    if @analysis_results["gender_appropriate"] == false
      raise ArgumentError, "This item does not match your gender preference"
    end

    # Validate inventory_item_id belongs to user if provided
    if inventory_item_id.present?
      item = user.inventory_items.find_by(id: inventory_item_id)
      unless item
        raise ArgumentError, "Inventory item not found or does not belong to you"
      end
    end
  end

  def sanitize_analysis_results(results)
    # Handle different input types
    sanitized = case results
    when ActionController::Parameters
      results.permit(
        :name, :description, :category_name, :category_matched, :subcategory,
        :material, :style, :style_notes,
        :brand_matched, :brand_name, :brand_suggestion,
        :gender_appropriate, :confidence, :extraction_prompt,
        colors: []
      ).to_h
    when Hash
      # Filter to only allowed keys for security
      permitted_keys = %w[
        name description category_name category_matched subcategory
        material style style_notes
        brand_matched brand_name brand_suggestion
        gender_appropriate confidence extraction_prompt colors
      ]
      results.slice(*permitted_keys)
    when String
      parsed = JSON.parse(results)
      if parsed.is_a?(Hash)
        permitted_keys = %w[
          name description category_name category_matched subcategory
          material style style_notes
          brand_matched brand_name brand_suggestion
          gender_appropriate confidence extraction_prompt colors
        ]
        parsed.slice(*permitted_keys)
      else
        parsed
      end
    else
      results
    end

    # Convert symbol keys to string keys for consistency
    if sanitized.is_a?(Hash)
      sanitized = sanitized.stringify_keys
    end
    sanitized
  end
end
