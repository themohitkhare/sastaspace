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
          primary_image_url: @inventory_item.primary_image.attached? ? url_for(@inventory_item.primary_image) : nil,
          additional_images: @inventory_item.additional_images.map { |img| url_for(img) },
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
      
      def url_for(attachment)
        Rails.application.routes.url_helpers.url_for(attachment)
      end
    end
  end
end
