module Services
  class BlobDeduplicationService
    # Find or create a blob, reusing existing blobs with the same checksum
    # This saves storage space by not duplicating identical images
    #
    # @param io [IO, File, ActionDispatch::Http::UploadedFile] The file/IO object to upload
    # @param filename [String] The filename
    # @param content_type [String] The content type
    # @return [ActiveStorage::Blob] The existing or newly created blob
    def self.find_or_create_blob(io:, filename:, content_type:)
      # Calculate checksum using ActiveStorage's built-in method
      # We need to reset the IO position after reading
      io.rewind if io.respond_to?(:rewind)
      checksum = ActiveStorage::Blob.compute_checksum(io)
      io.rewind if io.respond_to?(:rewind)

      # Try to find an existing blob with the same checksum
      existing_blob = ActiveStorage::Blob.find_by(checksum: checksum)

      if existing_blob
        # Get file size for logging (approximate from existing blob)
        saved_bytes = existing_blob.byte_size
        Rails.logger.info "Reusing existing blob #{existing_blob.id} for image with checksum #{checksum} (saved ~#{saved_bytes} bytes)"
        return existing_blob
      end

      # No existing blob found, create a new one
      Rails.logger.info "Creating new blob for image with checksum #{checksum}"
      ActiveStorage::Blob.create_and_upload!(
        io: io,
        filename: filename,
        content_type: content_type
      )
    rescue StandardError => e
      Rails.logger.error "Error in blob deduplication: #{e.message}"
      Rails.logger.error e.backtrace.first(5).join("\n")
      # Fallback to creating a new blob without deduplication
      io.rewind if io.respond_to?(:rewind)
      ActiveStorage::Blob.create_and_upload!(
        io: io,
        filename: filename,
        content_type: content_type
      )
    end
  end
end
