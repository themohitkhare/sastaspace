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

      # Create images directory
      images_dir = File.join(temp_dir, "images")
      FileUtils.mkdir_p(images_dir)

      # Collect and download all images
      image_index = 0
      user.inventory_items.each do |item|
        # Primary image
        if item.primary_image.attached?
          image_index += 1
          download_image(item.primary_image, images_dir, "item_#{item.id}_primary_#{image_index}")
        end

        # Additional images
        if item.additional_images.attached?
          item.additional_images.each_with_index do |image, idx|
            image_index += 1
            download_image(image, images_dir, "item_#{item.id}_additional_#{idx + 1}_#{image_index}")
          end
        end
      end

      # Create ZIP file
      zip_filename = "user_#{user_id}_export_#{Time.current.to_i}.zip"
      zip_path = EXPORT_DIR.join(zip_filename)

      Zip::File.open(zip_path, Zip::File::CREATE) do |zip_file|
        # Add JSON file
        zip_file.add("data.json", json_path)

        # Add all images
        Dir.glob(File.join(images_dir, "*")).each do |image_file|
          zip_file.add(File.join("images", File.basename(image_file)), image_file)
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
      FileUtils.rm_rf(temp_dir) if Dir.exist?(temp_dir)
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
    return unless attachment.attached?

    # Get file extension from content type or filename
    extension = if attachment.content_type
                  case attachment.content_type
                  when "image/jpeg", "image/jpg"
                    ".jpg"
                  when "image/png"
                    ".png"
                  when "image/webp"
                    ".webp"
                  when "image/gif"
                    ".gif"
                  else
                    File.extname(attachment.filename.to_s) || ".jpg"
                  end
    else
                  File.extname(attachment.filename.to_s) || ".jpg"
    end

    filename = "#{base_name}#{extension}"
    file_path = File.join(target_dir, filename)

    # Download the blob content and write to file
    image_data = attachment.blob.download
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
      if File.mtime(file) < cutoff_time
        File.delete(file)
        Rails.logger.info "Cleaned up old export: #{file}"
      end
    end
  end
end
