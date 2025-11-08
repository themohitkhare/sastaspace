module Services
  # Service for handling blob attachments to inventory items
  # Extracts blob attachment logic from controllers
  class BlobAttachmentService
    attr_reader :inventory_item, :session

    def initialize(inventory_item:, session: nil)
      @inventory_item = inventory_item
      @session = session
    end

    # Attach primary image from blob_id (from AI uploads)
    # @param blob_id [String, Integer] The blob ID to attach
    # @return [Boolean] true if attachment succeeded, false otherwise
    def attach_primary_image_from_blob_id(blob_id)
      return false unless blob_id.present?

      begin
        blob_id_int = blob_id.to_i
        blob = ActiveStorage::Blob.find_by(id: blob_id_int)

        unless blob
          Rails.logger.error "Blob #{blob_id_int} not found in database"
          return false
        end

        # Remove existing primary image if any
        @inventory_item.primary_image_attachment&.purge
        @inventory_item.primary_image.attach(blob)

        # Reload to ensure attachment is available
        @inventory_item.reload
        attachment = @inventory_item.primary_image_attachment

        if attachment && attachment.persisted?
          Rails.logger.info "Successfully attached blob #{blob.id} as primary image for inventory item #{@inventory_item.id}"
          # Clear session blob_id if it was used
          clear_session_blob_id(blob_id_int) if @session
          true
        else
          Rails.logger.error "Attachment not found or not persisted after attach! Item ID: #{@inventory_item.id}, Blob ID: #{blob.id}"
          # Try attaching again as fallback
          @inventory_item.primary_image.attach(blob)
          @inventory_item.reload

          if @inventory_item.primary_image_attachment&.persisted?
            Rails.logger.info "Attachment succeeded on retry"
            clear_session_blob_id(blob_id_int) if @session
            true
          else
            Rails.logger.error "Attachment FAILED even after retry!"
            false
          end
        end
      rescue ActiveRecord::RecordNotFound => e
        Rails.logger.error "Blob #{blob_id_int} not found for inventory item: #{e.message}"
        false
      rescue StandardError => e
        Rails.logger.error "Error attaching blob to inventory item: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
        false
      end
    end

    # Attach primary image from uploaded file
    # @param uploaded_file [ActionDispatch::Http::UploadedFile] The uploaded file
    # @return [Boolean] true if attachment succeeded, false otherwise
    def attach_primary_image_from_file(uploaded_file)
      return false unless uploaded_file.present?

      begin
        blob = Services::BlobDeduplicationService.find_or_create_blob(
          io: uploaded_file.open,
          filename: uploaded_file.original_filename,
          content_type: uploaded_file.content_type
        )
        @inventory_item.primary_image_attachment&.purge
        @inventory_item.primary_image.attach(blob)
        true
      rescue StandardError => e
        Rails.logger.error "Error attaching primary image from file: #{e.message}"
        Rails.logger.error e.backtrace.first(5).join("\n")
        false
      end
    end

    # Attach additional images from uploaded files
    # @param uploaded_files [Array<ActionDispatch::Http::UploadedFile>] Array of uploaded files
    # @return [Integer] Number of images successfully attached
    def attach_additional_images_from_files(uploaded_files)
      return 0 unless uploaded_files.present?

      count = 0
      Array(uploaded_files).reject(&:blank?).each do |image|
        # Skip if not an uploaded file (could be empty string)
        next unless image.is_a?(ActionDispatch::Http::UploadedFile)

        begin
          blob = Services::BlobDeduplicationService.find_or_create_blob(
            io: image.open,
            filename: image.original_filename,
            content_type: image.content_type
          )
          @inventory_item.additional_images.attach(blob)
          count += 1
        rescue StandardError => e
          Rails.logger.error "Error attaching additional image: #{e.message}"
          Rails.logger.error e.backtrace.first(5).join("\n")
        end
      end
      count
    end

    # Handle blob_id from params or session (for AI uploads)
    # @param params_blob_id [String, Integer, nil] Blob ID from params
    # @return [Boolean] true if attachment succeeded, false otherwise
    def handle_blob_id_from_params_or_session(params_blob_id)
      # Check params first, then session
      blob_id = params_blob_id
      blob_id ||= @session[:pending_blob_id] if @session && @session[:pending_blob_id].present?

      return false unless blob_id.present?

      attach_primary_image_from_blob_id(blob_id)
    end

    private

    def clear_session_blob_id(blob_id_int)
      return unless @session

      if @session[:pending_blob_id].to_s == blob_id_int.to_s
        @session.delete(:pending_blob_id)
      end
    end
  end
end
