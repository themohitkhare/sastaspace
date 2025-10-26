require "test_helper"

module Api
  module V1
    class InventoryItemSerializerTest < ActiveSupport::TestCase
      def setup
        @user = create(:user)
        @category = create(:category, :clothing)
        @brand = create(:brand)
        @inventory_item = create(:inventory_item, :clothing,
          user: @user,
          category: @category,
          brand: @brand,
          metadata: { color: "blue", size: "M" }
        )
        @serializer = InventoryItemSerializer.new(@inventory_item)
      end

      test "should serialize basic inventory item attributes" do
        serialized = @serializer.as_json

        assert_equal @inventory_item.id, serialized[:id]
        assert_equal @inventory_item.name, serialized[:name]
        assert_equal @inventory_item.item_type, serialized[:item_type]
        assert_equal @inventory_item.description, serialized[:description]
        assert_equal @inventory_item.status, serialized[:status]
        assert_equal @inventory_item.purchase_price, serialized[:purchase_price]
        assert_equal @inventory_item.purchase_date, serialized[:purchase_date]
        assert_equal @inventory_item.wear_count, serialized[:wear_count]
        assert_equal @inventory_item.last_worn_at, serialized[:last_worn_at]
        assert_equal @inventory_item.created_at, serialized[:created_at]
        assert_equal @inventory_item.updated_at, serialized[:updated_at]
      end

      test "should serialize category information" do
        serialized = @serializer.as_json
        category = serialized[:category]

        assert_equal @category.id, category[:id]
        assert_equal @category.name, category[:name]
        assert_equal @category.description, category[:description]
      end

      test "should serialize brand information when present" do
        serialized = @serializer.as_json
        brand = serialized[:brand]

        assert_equal @brand.id, brand[:id]
        assert_equal @brand.name, brand[:name]
        assert_equal @brand.description, brand[:description]
      end

      test "should serialize nil brand when not present" do
        item_without_brand = create(:inventory_item, :clothing, brand: nil)
        serializer = InventoryItemSerializer.new(item_without_brand)
        serialized = serializer.as_json

        assert_nil serialized[:brand]
      end

      test "should serialize tags" do
        tag1 = create(:tag, name: "casual", color: "#blue")
        tag2 = create(:tag, name: "summer", color: "#yellow")
        @inventory_item.tags << [ tag1, tag2 ]

        serialized = @serializer.as_json
        tags = serialized[:tags]

        assert_equal 2, tags.length
        assert_includes tags.map { |t| t[:name] }, "casual"
        assert_includes tags.map { |t| t[:name] }, "summer"
      end

      test "should serialize metadata summary" do
        serialized = @serializer.as_json
        metadata = serialized[:metadata]

        assert_equal "blue", metadata[:color]
        assert_equal "M", metadata[:size]
      end

      test "should serialize images structure" do
        serialized = @serializer.as_json
        images = serialized[:images]

        assert_includes images.keys, :primary
        assert_includes images.keys, :additional
      end

      test "should serialize primary image with variants when attached" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        serialized = @serializer.as_json
        primary_image = serialized[:images][:primary]

        assert_not_nil primary_image
        assert_equal @inventory_item.primary_image.id, primary_image[:id]
        assert_equal "test.jpg", primary_image[:filename]
        assert_equal "image/jpeg", primary_image[:content_type]
        assert_equal @inventory_item.primary_image.byte_size, primary_image[:byte_size]

        # Check URLs structure
        urls = primary_image[:urls]
        assert_includes urls.keys, :original
        assert_includes urls.keys, :thumb
        assert_includes urls.keys, :medium
        assert_includes urls.keys, :large
      end

      test "should serialize nil primary image when not attached" do
        serialized = @serializer.as_json
        primary_image = serialized[:images][:primary]

        assert_nil primary_image
      end

      test "should serialize additional images with variants when attached" do
        @inventory_item.additional_images.attach([
          {
            io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
            filename: "test1.jpg",
            content_type: "image/jpeg"
          },
          {
            io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
            filename: "test2.jpg",
            content_type: "image/jpeg"
          }
        ])

        serialized = @serializer.as_json
        additional_images = serialized[:images][:additional]

        assert_equal 2, additional_images.length

        additional_images.each do |image|
          assert_includes image.keys, :id
          assert_includes image.keys, :filename
          assert_includes image.keys, :content_type
          assert_includes image.keys, :byte_size
          assert_includes image.keys, :urls

          urls = image[:urls]
          assert_includes urls.keys, :original
          assert_includes urls.keys, :thumb
          assert_includes urls.keys, :medium
          assert_includes urls.keys, :large
        end
      end

      test "should serialize empty additional images array when none attached" do
        serialized = @serializer.as_json
        additional_images = serialized[:images][:additional]

        assert_equal [], additional_images
      end

      test "serialize_image_with_variants should return nil for unattached image" do
        unattached_image = @inventory_item.primary_image
        result = @serializer.send(:serialize_image_with_variants, unattached_image)

        assert_nil result
      end

      test "serialize_image_with_variants should return proper structure for attached image" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        result = @serializer.send(:serialize_image_with_variants, @inventory_item.primary_image)

        assert_includes result.keys, :id
        assert_includes result.keys, :filename
        assert_includes result.keys, :content_type
        assert_includes result.keys, :byte_size
        assert_includes result.keys, :urls
      end
    end
  end
end
