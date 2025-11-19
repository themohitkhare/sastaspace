class ClothingDetectionJob < ApplicationJob
  # User-facing detection operations
  queue_as :default

  # No discard_on or retry_on for this critical job - all failures should be visible

  # Class method to get job status
  def self.get_status(job_id)
    key = "clothing_detection_job:#{job_id}"
    cached_status = Rails.cache.read(key)

    if cached_status.present?
      return cached_status.is_a?(Hash) ? cached_status.stringify_keys : cached_status
    end

    # Try to recover from Sidekiq
    recovered_status = recover_from_sidekiq(job_id)
    return recovered_status if recovered_status.present?

    # Job not found
    {
      "status" => "not_found",
      "error" => { "message" => "Job not found or expired. If the job was recently queued, it may still be processing." },
      "updated_at" => Time.current.iso8601
    }
  rescue StandardError => e
    Rails.logger.error "Error reading job status for ClothingDetectionJob: #{e.message}"
    { "status" => "error", "error" => "Could not retrieve job status" }
  end

  # Recover job status from Sidekiq
  def self.recover_from_sidekiq(job_id)
    return nil unless defined?(Sidekiq)

    # Check scheduled queue
    scheduled = Sidekiq::ScheduledSet.new
    job = scheduled.find { |j| j.jid == job_id }
    if job
      return {
        "status" => "scheduled",
        "updated_at" => Time.at(job.score).iso8601,
        "recovered" => true
      }
    end

    # Check retry queue
    retries = Sidekiq::RetrySet.new
    job = retries.find { |j| j.jid == job_id }
    if job
      return {
        "status" => "retrying",
        "error" => { "message" => job.item["error_message"] || "Job is retrying" },
        "updated_at" => Time.at(job.score).iso8601,
        "recovered" => true
      }
    end

    # Check dead queue
    dead = Sidekiq::DeadSet.new
    job = dead.find { |j| j.jid == job_id }
    if job
      return {
        "status" => "failed",
        "error" => { "message" => job.item["error_message"] || "Job failed" },
        "updated_at" => Time.at(job.score).iso8601,
        "recovered" => true
      }
    end

    nil
  rescue StandardError => e
    Rails.logger.warn "Failed to recover job status from Sidekiq: #{e.message}"
    nil
  end

  def perform(image_blob_id, user_id, options = {})
    @image_blob = ActiveStorage::Blob.find(image_blob_id)
    @user = User.find(user_id)
    @options = options.with_indifferent_access

    Rails.logger.info "Starting clothing detection job for user #{user_id}, blob #{image_blob_id}"

    # Update job status in cache
    update_job_status("processing", { message: "Starting clothing detection analysis..." })

    # Update job status
    update_progress("Starting clothing detection analysis...")

    # Run detection
    detection_service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: @user,
      model_name: @options[:model_name] || "qwen3-vl:8b"
    )

    update_job_status("processing", { message: "Analyzing image for clothing items..." })
    update_progress("Analyzing image for clothing items...")
    analysis_result = detection_service.analyze

    # Check if analysis failed
    if analysis_result["error"].present?
      update_job_status("failed", nil, analysis_result["error"])
      handle_detection_error(analysis_result["error"])
      return
    end

    # Find or create analysis record
    analysis = ClothingAnalysis.find_by(id: analysis_result["analysis_id"]) if analysis_result["analysis_id"].present?

    unless analysis
      # Create analysis record if it doesn't exist
      analysis = ClothingAnalysis.create!(
        user: @user,
        image_blob_id: @image_blob.id,
        parsed_data: analysis_result,
        items_detected: analysis_result["total_items_detected"] || 0,
        confidence: calculate_average_confidence(analysis_result),
        status: "completed"
      )
    end

    update_progress("Detection completed successfully")

    # Automatically create inventory items from detected items
    created_items = create_inventory_items_from_detection(analysis, analysis_result)

    # Update job status to completed
    update_job_status("completed", {
      analysis_id: analysis.id,
      items_detected: analysis_result["total_items_detected"] || 0,
      items: analysis_result["items"] || [],
      created_items_count: created_items.count
    })

    # Notify frontend of completion
    broadcast_detection_complete(
      analysis_id: analysis.id,
      items_detected: analysis_result["total_items_detected"] || 0,
      items: analysis_result["items"] || [],
      created_items_count: created_items.count
    )

    Rails.logger.info "Detection completed: #{analysis_result['total_items_detected']} items found, #{created_items.count} items created for user #{user_id}"
  rescue ActiveRecord::RecordNotFound => e
    Rails.logger.error "Record not found in ClothingDetectionJob: #{e.message}"
    update_job_status("failed", nil, "Image or user not found")
    broadcast_detection_error("Image or user not found")
    raise
  rescue StandardError => e
    update_job_status("failed", nil, e.message)
    handle_general_error(e)
    raise
  end

  private

  def update_job_status(status, data = nil, error = nil)
    return unless job_id.present?

    status_data = {
      "status" => status,
      "data" => data,
      "error" => error,
      "updated_at" => Time.current.iso8601
    }

    key = "clothing_detection_job:#{job_id}"
    Rails.cache.write(key, status_data, expires_in: 1.hour)
  end

  def update_progress(message)
    broadcast_progress(message)
  end

  def broadcast_progress(message)
    ActionCable.server.broadcast(
      "detection_#{@user.id}",
      {
        type: "progress_update",
        message: message,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_detection_complete(analysis_id:, items_detected:, items:, created_items_count: 0)
    ActionCable.server.broadcast(
      "detection_#{@user.id}",
      {
        type: "detection_complete",
        analysis_id: analysis_id,
        items_detected: items_detected,
        items: items,
        created_items_count: created_items_count,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def broadcast_detection_error(error_message)
    # @user might be nil if error occurred during initialization
    return unless @user&.id

    ActionCable.server.broadcast(
      "detection_#{@user.id}",
      {
        type: "detection_error",
        error: error_message,
        job_id: job_id,
        timestamp: Time.current.iso8601
      }
    )
  end

  def handle_detection_error(error_message)
    Rails.logger.error "Clothing detection failed: #{error_message}"
    broadcast_detection_error(error_message)

    # Create failed analysis record
    ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: { "error" => error_message },
      items_detected: 0,
      status: "failed"
    )
  end

  def handle_general_error(error)
    error_message = "Analysis failed: #{error.message}"
    Rails.logger.error "ClothingDetectionJob error: #{error_message}"
    Rails.logger.error error.backtrace.first(10).join("\n")
    broadcast_detection_error(error_message)
  end

  def calculate_average_confidence(analysis_result)
    items = analysis_result["items"] || []
    return nil if items.empty?

    confidences = items.map { |item| item["confidence"] || 0.0 }.compact
    return nil if confidences.empty?

    (confidences.sum.to_f / confidences.length).round(2)
  end

  def create_inventory_items_from_detection(analysis, analysis_result)
    items = analysis_result["items"] || []
    return [] if items.empty?

    created_items = []

    items.each do |item_data|
      begin
        # Skip if item_data is nil or not a hash
        next unless item_data.is_a?(Hash)

        # Build item params from detected item data
        # Use LLM-generated description if available, otherwise build one
        description = (item_data["description"] || item_data[:description]).presence || build_item_description(item_data)

        # Handle both string and symbol keys
        # Extract extraction_prompt if available
        extraction_prompt = item_data["extraction_prompt"] || item_data[:extraction_prompt]

        item_params = {
          name: item_data["item_name"] || item_data[:item_name] || "Detected Item",
          description: description,
          category_id: item_data["category_id"] || item_data[:category_id],
          status: "active",
          extraction_prompt: extraction_prompt, # Store extraction_prompt for stock photo extraction
          clothing_analysis: analysis,
          metadata: {
            color: item_data["color_primary"] || item_data[:color_primary],
            material: item_data["material_type"] || item_data[:material_type],
            style_category: item_data["style_category"] || item_data[:style_category],
            gender_styling: item_data["gender_styling"] || item_data[:gender_styling],
            pattern_type: item_data["pattern_type"] || item_data[:pattern_type],
            pattern_details: item_data["pattern_details"] || item_data[:pattern_details]
          }
        }

        # Build inventory item
        inventory_item = @user.inventory_items.build(item_params)

        # Normalize category/subcategory
        if inventory_item.category_id.present?
          selected = Category.find_by(id: inventory_item.category_id)
          if selected&.parent_id.present?
            inventory_item.subcategory_id = selected.id
            node = selected
            node = node.respond_to?(:parent_category) ? node.parent_category : node.parent while node&.parent_id.present?
            inventory_item.category_id = node&.id || selected.id
          end
        end

        if inventory_item.save
          # Attach the image blob to the item
          if @image_blob.present?
            attachment_service = Services::BlobAttachmentService.new(inventory_item: inventory_item)
            attachment_service.attach_primary_image_from_blob_id(@image_blob.id)
            inventory_item.reload
          end

          created_items << inventory_item
          Rails.logger.info "Created inventory item #{inventory_item.id} from detection"

          # Automatically trigger stock photo extraction for this item
          trigger_stock_photo_extraction(inventory_item, item_data)
        else
          Rails.logger.error "Failed to create inventory item: #{inventory_item.errors.full_messages.join(', ')}"
        end
      rescue StandardError => e
        Rails.logger.error "Error creating inventory item from detection: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
      end
    end

    created_items
  end

  def build_item_description(item_data)
    # Build a rich, descriptive text from all available data
    return "Detected clothing item from image analysis." unless item_data.is_a?(Hash)

    # Start with item name (handle both string and symbol keys)
    item_name = item_data["item_name"] || item_data[:item_name] || "Clothing item"
    subcategory = item_data["subcategory"] || item_data[:subcategory]

    # Build the main description sentence
    main_desc = item_name
    if subcategory.present? && !item_name.downcase.include?(subcategory.downcase)
      main_desc = "#{item_name} (#{subcategory})"
    end

    # Collect all descriptive details
    detail_parts = []

    # Add color information (handle both string and symbol keys)
    color_primary = item_data["color_primary"] || item_data[:color_primary]
    if color_primary.present?
      color_desc = color_primary.to_s
      color_secondary = item_data["color_secondary"] || item_data[:color_secondary]
      color_desc += " and #{color_secondary}" if color_secondary.present?
      detail_parts << "in #{color_desc}"
    end

    # Add material information
    material = item_data["material_type"] || item_data[:material_type]
    if material.present?
      detail_parts << "made of #{material}"
    end

    # Add pattern information
    pattern_type = item_data["pattern_type"] || item_data[:pattern_type]
    if pattern_type.present? && pattern_type.to_s != "solid"
      pattern_desc = item_data["pattern_details"] || item_data[:pattern_details] || pattern_type
      detail_parts << "featuring #{pattern_desc} pattern"
    end

    # Add style information
    style_category = item_data["style_category"] || item_data[:style_category]
    if style_category.present?
      detail_parts << "#{style_category} style"
    end

    # Add gender styling
    gender_styling = item_data["gender_styling"] || item_data[:gender_styling]
    gender_desc = case gender_styling
    when "men", :men
                    "men's"
    when "women", :women
                    "women's"
    when "unisex", :unisex
                    "unisex"
    else
                    nil
    end
    detail_parts << "#{gender_desc} styling" if gender_desc

    # Build comprehensive description as natural sentence
    description = main_desc

    if detail_parts.any?
      # Capitalize first letter of detail parts, but preserve the rest
      details_text = detail_parts.join(", ")
      details_text = details_text[0].upcase + details_text[1..-1] if details_text.present?
      description += ". " + details_text + "."
    else
      description += "."
    end

    # Ensure proper capitalization of first letter only
    description = description.strip
    description = description[0].upcase + description[1..-1] if description.present?

    description.presence || "Detected clothing item from image analysis."
  end

  def trigger_stock_photo_extraction(inventory_item, item_data)
    return unless @image_blob.present? && inventory_item.primary_image.attached?

    begin
      # Build analysis_results hash from item_data for extraction
      analysis_results = {
        name: inventory_item.name,
        description: inventory_item.description,
        category_name: inventory_item.category&.name,
        category_matched: inventory_item.category&.name,
        subcategory: inventory_item.subcategory&.name,
        material: item_data["material_type"] || item_data[:material_type] || inventory_item.material,
        style: item_data["style_category"] || item_data[:style_category] || inventory_item.style_notes,
        style_notes: item_data["style_category"] || item_data[:style_category] || inventory_item.style_notes,
        brand_matched: inventory_item.brand&.name,
        colors: [ item_data["color_primary"] || item_data[:color_primary] || inventory_item.color ].compact,
        extraction_prompt: item_data["extraction_prompt"] || item_data[:extraction_prompt] || inventory_item.extraction_prompt,
        gender_appropriate: true,
        confidence: item_data["confidence"] || item_data[:confidence] || 0.9
      }

      # Use service object to queue extraction (reuses validation and sanitization)
      service = StockPhotoExtractionService.new(
        image_blob: @image_blob,
        user: @user,
        analysis_results: analysis_results,
        inventory_item_id: inventory_item.id
      )

      job_id = service.queue_extraction
      Rails.logger.info "Queued stock photo extraction for inventory item #{inventory_item.id} (job: #{job_id})"
    rescue ArgumentError => e
      Rails.logger.warn "Validation failed for stock photo extraction (item #{inventory_item.id}): #{e.message}"
      # Don't fail the main job if extraction validation fails
    rescue StandardError => e
      Rails.logger.error "Failed to queue stock photo extraction for inventory item #{inventory_item.id}: #{e.message}"
      Rails.logger.error e.backtrace.first(5).join("\n")
      # Don't fail the main job if extraction queuing fails
    end
  end
end
