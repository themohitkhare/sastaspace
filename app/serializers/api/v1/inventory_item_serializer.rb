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
          status: @inventory_item.status,
          category: serialize_category(@inventory_item.category),
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
      end

      private

      def serialize_category(category)
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
          {
            id: image.id,
            filename: image.filename.to_s,
            content_type: image.content_type,
            byte_size: image.byte_size,
            urls: {
              original: url_for(image),
              thumb: safe_variant_url(image, [ 150, 150 ]),
              medium: safe_variant_url(image, [ 400, 400 ]),
              large: safe_variant_url(image, [ 800, 800 ])
            }
          }
        rescue StandardError => e
          Rails.logger.warn "Failed to serialize image: #{e.message}"
          {
            id: image.id,
            filename: image.filename.to_s,
            content_type: image.content_type,
            byte_size: image.byte_size,
            urls: {
              original: nil,
              thumb: nil,
              medium: nil,
              large: nil
            }
          }
        end
      end

      def url_for(attachment)
        Rails.application.routes.url_helpers.url_for(attachment)
      rescue StandardError => e
        Rails.logger.warn "Failed to generate URL for attachment: #{e.message}"
        nil
      end

      def safe_variant_url(image, dimensions)
        variant = image.variant(resize_to_limit: dimensions)
        url_for(variant)
      rescue StandardError => e
        Rails.logger.warn "Failed to generate variant URL: #{e.message}"
        nil
      end
    end
  end
end
