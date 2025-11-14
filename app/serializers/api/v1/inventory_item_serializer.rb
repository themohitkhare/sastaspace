module Api
  module V1
    class InventoryItemSerializer
      def initialize(inventory_item)
        @inventory_item = inventory_item
      end

      def as_json
        {
          id: @inventory_item.id,
          name: @inventory_item.name,
          item_type: @inventory_item.item_type,
          description: @inventory_item.description,
          extraction_prompt: @inventory_item.extraction_prompt,
          status: @inventory_item.status,
          category: @inventory_item.category ? serialize_category(@inventory_item.category) : nil,
          brand: @inventory_item.brand ? serialize_brand(@inventory_item.brand) : nil,
          tags: @inventory_item.tags.map { |tag| serialize_tag(tag) },
          metadata: @inventory_item.metadata_summary,
          purchase_price: @inventory_item.purchase_price,
          purchase_date: @inventory_item.purchase_date,
          wear_count: @inventory_item.wear_count,
          last_worn_at: @inventory_item.last_worn_at,
          images: {
            primary: serialize_image_with_variants(@inventory_item.primary_image),

         additional: @inventory_item.additional_images.attached? ? @inventory_item.additional_images.map { |img| serialize_image_with_variants(img) } : []
          },
          created_at: @inventory_item.created_at,
          updated_at: @inventory_item.updated_at
        }
      rescue StandardError => e
        Rails.logger.error "Error in InventoryItemSerializer#as_json: #{e.message}"
        Rails.logger.error e.backtrace.first(10).join("\n")
        raise
      end

      private

      def serialize_category(category)
        return nil unless category

        {
          id: category.id,
          name: category.name,
          description: category.description
        }
      end

      def serialize_brand(brand)
        {
          id: brand.id,
          name: brand.name,
          description: brand.description
        }
      end

      def serialize_tag(tag)
        {
          id: tag.id,
          name: tag.name,
          color: tag.color
        }
      end

      def serialize_image_with_variants(image)
        return nil if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

        begin
          # Get original URL first as fallback for all variants
          original_url = url_for(image)

          # ActiveStorage::Attached::One delegates id, filename, etc. to blob
          # So we can call these methods directly on the image object
          {
            id: image.id,
            blob_id: image.blob.id, # Include blob_id for stock photo extraction
            filename: image.filename.to_s,
            content_type: image.content_type,
            byte_size: image.byte_size,
            urls: {
              original: original_url,
              thumb: safe_variant_url(image, [ 150, 150 ]) || original_url,
              medium: safe_variant_url(image, [ 400, 400 ]) || original_url,
              large: safe_variant_url(image, [ 800, 800 ]) || original_url
            }
          }
        rescue StandardError => e
          Rails.logger.warn "Failed to serialize image: #{e.message}"
          Rails.logger.warn e.backtrace.first(3).join("\n") if Rails.logger
          # Try to get basic info if available
          begin
            {
              id: image.id,
              filename: image.filename&.to_s,
              content_type: image.content_type,
              byte_size: image.byte_size,
              urls: {
                original: nil,
                thumb: nil,
                medium: nil,
                large: nil
              }
            }
          rescue StandardError
            # If even basic info fails, return minimal structure
            {
              id: nil,
              filename: nil,
              content_type: nil,
              byte_size: nil,
              urls: {
                original: nil,
                thumb: nil,
                medium: nil,
                large: nil
              }
            }
          end
        end
      end

      def url_for(attachment)
        # Use rails_blob_url helper for better URL generation
        return nil unless attachment.attached?

        # Try using rails_blob_url first (more reliable)
        begin
          url_options = { host: default_host, protocol: default_protocol }
          url_options[:port] = default_port if default_port
          Rails.application.routes.url_helpers.rails_blob_url(attachment, **url_options)
        rescue StandardError => e1
          Rails.logger.warn "rails_blob_url failed: #{e1.message}, trying url_for"
          # Fallback to url_for with options
          begin
            url_options = { host: default_host, protocol: default_protocol }
            url_options[:port] = default_port if default_port
            Rails.application.routes.url_helpers.url_for(attachment, **url_options)
          rescue StandardError => e2
            Rails.logger.warn "Failed to generate URL for attachment: #{e2.message}"
            Rails.logger.warn e2.backtrace.first(3).join("\n") if Rails.logger
            nil
          end
        end
      end

      def safe_variant_url(image, dimensions)
        return nil unless image.attached?

        # Try to generate variant URL, but catch errors gracefully
        # This prevents 500 errors when VIPS/ImageMagick is not installed
        begin
          # Check if variant can be created (this will fail if processor is not available)
          variant = image.variant(resize_to_limit: dimensions)

          # If variant creation succeeded, generate URL
          url_options = { host: default_host, protocol: default_protocol }
          url_options[:port] = default_port if default_port
          Rails.application.routes.url_helpers.rails_representation_url(variant, **url_options)
        rescue LoadError, NoMethodError, RuntimeError => e
          # These errors typically indicate VIPS/ImageMagick is not installed
          # Return nil so caller can use original image URL as fallback
          Rails.logger.debug "Variant processor not available (#{dimensions.join('x')}): #{e.class.name}"
          nil
        rescue StandardError => e
          # Other errors (e.g., invalid image, processing failure)
          Rails.logger.debug "Variant generation failed (#{dimensions.join('x')}): #{e.class.name} - #{e.message}"
          nil
        end
      end

      def default_host
        Rails.application.config.action_controller.default_url_options[:host] ||
          Rails.application.routes.default_url_options[:host] ||
          "localhost"
      end

      def default_port
        Rails.application.config.action_controller.default_url_options[:port] ||
          Rails.application.routes.default_url_options[:port] ||
          (Rails.env.development? ? 3000 : nil)
      end

      def default_protocol
        Rails.env.production? ? "https" : "http"
      end
    end
  end
end
