class BatchInventoryCreationJob < ApplicationJob
  # Lower priority queue for bulk processing operations
  queue_as :ai_batch

  # Don't retry StandardError - let errors bubble up for visibility
  # Only discard truly unrecoverable errors
  discard_on ActiveStorage::FileNotFoundError

  def perform(extraction_result_ids, user_id)
    @user = User.find(user_id)
    # Load extraction results - filter by user for security
    # Using a subquery to ensure we only get results for this user
    user_analysis_ids = ClothingAnalysis.where(user_id: @user.id).pluck(:id)
    @extraction_results = ExtractionResult
      .where(id: extraction_result_ids, clothing_analysis_id: user_analysis_ids)
      .includes(:clothing_analysis)

    Rails.logger.info "Starting batch inventory creation for #{@extraction_results.count} items"

    created_items = []

    @extraction_results.each do |result|
      unless result.extraction_successful?
        Rails.logger.warn "Skipping extraction result #{result.id}: not successful (status: #{result.status}, blob_id: #{result.extracted_image_blob_id})"
        next
      end

      begin
        # Create inventory item from extraction result
        item = create_inventory_item_from_extraction(result)
        created_items << item

        Rails.logger.info "Created inventory item #{item.id} from extraction result #{result.id}"
      rescue StandardError => e
        Rails.logger.error "Failed to create inventory item from extraction result #{result.id}: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
        # Re-raise in test environment to see the actual error
        raise if Rails.env.test?
      end
    end

    Rails.logger.info "Batch inventory creation completed: #{created_items.count} items created"

    # Broadcast completion
    broadcast_batch_complete(created_items.count, @extraction_results.count)
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error "Record not found in BatchInventoryCreationJob: #{e.message}"
    raise
  rescue StandardError => e
    Rails.logger.error "BatchInventoryCreationJob failed: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")
    raise
  end

  private

  def create_inventory_item_from_extraction(result)
    item_data = result.item_data_hash
    analysis = result.clothing_analysis

    # Handle both string and symbol keys
    item_name = item_data["item_name"] || item_data[:item_name] || "Extracted Item"
    description = item_data["description"] || item_data[:description] || ""
    category_name = item_data["category"] || item_data[:category]
    brand_name = item_data["brand_name"] || item_data[:brand_name]
    extraction_prompt = item_data["extraction_prompt"] || item_data[:extraction_prompt]

    # Create inventory item with extracted data
    inventory_item = InventoryItem.create!(
      user: @user,
      name: item_name,
      description: description,
      extraction_prompt: extraction_prompt,
      category: find_or_create_category(category_name),
      brand: find_or_create_brand(brand_name),
      clothing_analysis: analysis
    )

    # Attach the image blob if available
    if result.extracted_image_blob_id.present?
      attachment_service = Services::BlobAttachmentService.new(inventory_item: inventory_item)
      attachment_service.attach_primary_image_from_blob_id(result.extracted_image_blob_id)
      inventory_item.reload
    end

    inventory_item
  end

  def find_or_create_category(category_name)
    return default_category unless category_name.present?

    Category.find_or_create_by!(name: category_name)
  end

  def find_or_create_brand(brand_name)
    return nil unless brand_name.present?

    Brand.find_or_create_by!(name: brand_name)
  end

  def default_category
    # InventoryItem requires a category, so use a default "Uncategorized" category
    Category.find_or_create_by!(name: "Uncategorized") do |cat|
      cat.description = "Items without a specific category"
    end
  end

  def broadcast_batch_complete(created_count, total_count)
    # Broadcast to user's channel if needed
    ActionCable.server.broadcast(
      "batch_creation_#{@user.id}",
      {
        type: "batch_creation_complete",
        created_count: created_count,
        total_count: total_count,
        timestamp: Time.current.iso8601
      }
    )
  end
end
