# GDPR Data Export Job
# Exports all user data in JSON format for data portability (GDPR Article 20)
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
    export_data = generate_export(user)

    # Create export directory if it doesn't exist
    FileUtils.mkdir_p(EXPORT_DIR)

    # Generate filename with timestamp
    filename = "user_#{user_id}_export_#{Time.current.to_i}.json"
    file_path = EXPORT_DIR.join(filename)

    # Write export to file
    File.write(file_path, JSON.pretty_generate(export_data))

    # Store job status in cache with expiry
    status_data = {
      "status" => "completed",
      "file_path" => file_path.to_s,
      "download_url" => nil, # Could be a signed URL in production
      "expires_at" => (Time.current + EXPORT_EXPIRY).iso8601,
      "created_at" => Time.current.iso8601
    }

    cache_key = "export_job:#{job_id}:#{user_id}"
    self.class.write_status(cache_key, status_data, EXPORT_EXPIRY)

    Rails.logger.info "GDPR export completed for user #{user_id}, job #{job_id}"

    # Clean up old exports (older than expiry)
    cleanup_old_exports(user_id)
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
          results: analysis.results,
          created_at: analysis.created_at.iso8601
        }
      end
    }
  end

  def cleanup_old_exports(user_id)
    # Remove exports older than expiry time
    cutoff_time = Time.current - EXPORT_EXPIRY
    Dir.glob(EXPORT_DIR.join("user_#{user_id}_export_*.json")).each do |file|
      if File.mtime(file) < cutoff_time
        File.delete(file)
        Rails.logger.info "Cleaned up old export: #{file}"
      end
    end
  end
end
