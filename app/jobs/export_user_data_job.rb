# GDPR Data Export Job
# Exports all user data in ZIP format (JSON + images) for data portability (GDPR Article 20)
require "zip"

class ExportUserDataJob < ApplicationJob
  queue_as :default

  # Export directory for user data
  EXPORT_DIR = Rails.root.join("tmp", "exports").freeze
  EXPORT_EXPIRY = 7.days

  # In-memory store for test environment (when cache is null_store)
  @test_status_store = {} if Rails.env.test?

  def perform(user_id, job_id)
    user = User.find_by(id: user_id)
    unless user
      Rails.logger.error "GDPR export failed: User #{user_id} not found"
      status_data = {
        "status" => "failed",
        "error" => "User not found",
        "created_at" => Time.current.iso8601
      }
      cache_key = "export_job:#{job_id}:#{user_id}"
      self.class.write_status(cache_key, status_data, 1.hour)
      return
    end

    # Create export directory if it doesn't exist
    FileUtils.mkdir_p(EXPORT_DIR)

    # Create temporary directory for building the export
    temp_dir = Dir.mktmpdir("export_#{user_id}_")
    begin
      # Generate export data
      export_data = generate_export(user)

      # Write JSON file
      json_path = File.join(temp_dir, "data.json")
      File.write(json_path, JSON.pretty_generate(export_data))

      # Verify file was written successfully
      unless File.exist?(json_path)
        raise "Failed to write data.json to #{json_path}"
      end

      # Create images directory
      images_dir = File.join(temp_dir, "images")
      FileUtils.mkdir_p(images_dir)

      # Collect and download all images
      # Eager load attachments to avoid N+1 queries
      image_index = 0
      user.inventory_items.with_attached_primary_image.with_attached_additional_images.each do |item|
        # Primary image
        if item.primary_image.attached?
          image_index += 1
          download_image(item.primary_image, images_dir, "item_#{item.id}_primary_#{image_index}")
        end

        # Additional images - directly iterate over the collection
        # with_attached_additional_images ensures they're loaded
        item.additional_images.each_with_index do |image, idx|
          image_index += 1
          download_image(image, images_dir, "item_#{item.id}_additional_#{idx + 1}_#{image_index}")
        end
      end

      # Create ZIP file
      # Use microseconds for uniqueness to avoid collisions in parallel tests
      zip_filename = "user_#{user_id}_export_#{Time.current.to_f.to_s.gsub('.', '_')}.zip"
      zip_path = EXPORT_DIR.join(zip_filename)

      # Delete existing ZIP file if it exists (from previous test runs or collisions)
      # This ensures we always create a fresh ZIP file
      File.delete(zip_path) if File.exist?(zip_path)

      Zip::File.open(zip_path, Zip::File::CREATE) do |zip_file|
        # Add JSON file (verify it exists first)
        if File.exist?(json_path)
          zip_file.add("data.json", json_path)
        else
          raise "data.json file not found at #{json_path}"
        end

        # Add all images (only if they exist)
        Dir.glob(File.join(images_dir, "*")).each do |image_file|
          if File.exist?(image_file)
            zip_file.add(File.join("images", File.basename(image_file)), image_file)
          end
        end
      end

      # Store job status in cache with expiry
      status_data = {
        "status" => "completed",
        "file_path" => zip_path.to_s,
        "download_url" => nil, # Could be a signed URL in production
        "expires_at" => (Time.current + EXPORT_EXPIRY).iso8601,
        "created_at" => Time.current.iso8601
      }

      cache_key = "export_job:#{job_id}:#{user_id}"
      self.class.write_status(cache_key, status_data, EXPORT_EXPIRY)

      Rails.logger.info "GDPR export completed for user #{user_id}, job #{job_id}, ZIP: #{zip_filename}"

      # Clean up old exports (older than expiry)
      cleanup_old_exports(user_id)
    ensure
      # Clean up temporary directory
      # Use force option to ensure cleanup even if files are locked
      if Dir.exist?(temp_dir)
        begin
          FileUtils.rm_rf(temp_dir, secure: true)
        rescue StandardError => e
          Rails.logger.warn "Failed to clean up temp directory #{temp_dir}: #{e.message}"
          # Try again with a delay in case files are still in use
          sleep 0.1
          FileUtils.rm_rf(temp_dir, secure: true) rescue nil
        end
      end
    end
  rescue StandardError => e
    Rails.logger.error "GDPR export failed for user #{user_id}, job #{job_id}: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")

    # Store failure status
    status_data = {
      "status" => "failed",
      "error" => e.message,
      "created_at" => Time.current.iso8601
    }
    cache_key = "export_job:#{job_id}:#{user_id}"
    self.class.write_status(cache_key, status_data, 1.hour)
    raise e
  end

  # Get job status from cache
  def self.get_status(job_id, user_id)
    cache_key = "export_job:#{job_id}:#{user_id}"
    status = read_status(cache_key)
    return { "status" => "not_found" } unless status

    # Convert symbol keys to string keys for consistency
    status.is_a?(Hash) ? status.stringify_keys : status
  end

  # Write status (handles test environment with null_store)
  def self.write_status(cache_key, status_data, expires_in)
    if Rails.env.test? && Rails.cache.is_a?(ActiveSupport::Cache::NullStore)
      # Use in-memory store for tests
      @test_status_store ||= {}
      @test_status_store[cache_key] = status_data
    else
      Rails.cache.write(cache_key, status_data, expires_in: expires_in)
    end
  end

  # Read status (handles test environment with null_store)
  def self.read_status(cache_key)
    if Rails.env.test? && Rails.cache.is_a?(ActiveSupport::Cache::NullStore)
      # Use in-memory store for tests
      @test_status_store ||= {}
      @test_status_store[cache_key]
    else
      Rails.cache.read(cache_key)
    end
  end

  private

  def generate_export(user)
    {
      export_metadata: {
        exported_at: Time.current.iso8601,
        user_id: user.id,
        format_version: "1.0"
      },
      user_profile: {
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        created_at: user.created_at.iso8601,
        updated_at: user.updated_at.iso8601
      },
      inventory_items: user.inventory_items.map do |item|
        {
          id: item.id,
          name: item.name,
          description: item.description,
          category: item.category&.name,
          brand: item.brand&.name,
          color: item.color,
          size: item.size,
          material: item.material,
          season: item.season,
          occasion: item.occasion,
          status: item.status,
          metadata: item.metadata,
          created_at: item.created_at.iso8601,
          updated_at: item.updated_at.iso8601,
          tags: item.tags.pluck(:name)
        }
      end,
      outfits: user.outfits.map do |outfit|
        {
          id: outfit.id,
          name: outfit.name,
          description: outfit.description,
          occasion: outfit.occasion,
          season: outfit.season,
          status: outfit.status,
          is_favorite: outfit.is_favorite,
          metadata: outfit.metadata,
          created_at: outfit.created_at.iso8601,
          updated_at: outfit.updated_at.iso8601,
          items: outfit.inventory_items.pluck(:id, :name)
        }
      end,
      ai_analyses: user.ai_analyses.map do |analysis|
        {
          id: analysis.id,
          inventory_item_id: analysis.inventory_item_id,
          analysis_type: analysis.analysis_type,
          confidence_score: analysis.confidence_score,
          analysis_data: analysis.analysis_data,
          created_at: analysis.created_at.iso8601
        }
      end
    }
  end

  def download_image(attachment, target_dir, base_name)
    # attachment can be either ActiveStorage::Attached::One or ActiveStorage::Attachment
    # Check if it's already an Attachment record or if it needs .attached? check
    if attachment.is_a?(ActiveStorage::Attachment)
      # It's already an attachment record, just use it
      actual_attachment = attachment
    else
      # It's an Attached::One, check if attached
      return unless attachment.attached?
      actual_attachment = attachment
    end

    # Get file extension from content type or filename
    extension = if actual_attachment.content_type
                  case actual_attachment.content_type
                  when "image/jpeg", "image/jpg"
                    ".jpg"
                  when "image/png"
                    ".png"
                  when "image/webp"
                    ".webp"
                  when "image/gif"
                    ".gif"
                  else
                    File.extname(actual_attachment.filename.to_s) || ".jpg"
                  end
    else
                  File.extname(actual_attachment.filename.to_s) || ".jpg"
    end

    filename = "#{base_name}#{extension}"
    file_path = File.join(target_dir, filename)

    # Download the blob content and write to file
    image_data = actual_attachment.blob.download
    File.binwrite(file_path, image_data)

    Rails.logger.debug "Downloaded image for export: #{filename}"
  rescue StandardError => e
    Rails.logger.warn "Failed to download image #{base_name} for export: #{e.message}"
    # Continue with export even if some images fail
  end

  def cleanup_old_exports(user_id)
    # Remove exports older than expiry time (both JSON and ZIP)
    cutoff_time = Time.current - EXPORT_EXPIRY
    Dir.glob(EXPORT_DIR.join("user_#{user_id}_export_*.*")).each do |file|
      # Check if file exists before accessing it (handles race conditions where file
      # might be deleted between Dir.glob and File.mtime)
      next unless File.exist?(file)

      begin
        if File.mtime(file) < cutoff_time
          File.delete(file)
          Rails.logger.info "Cleaned up old export: #{file}"
        end
      rescue Errno::ENOENT => e
        # File was deleted between existence check and mtime call
        Rails.logger.debug "File #{file} was deleted during cleanup: #{e.message}"
      end
    end
  end
end
