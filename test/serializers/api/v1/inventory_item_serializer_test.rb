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
        tag1_name = "casual #{SecureRandom.hex(4)}"
        tag2_name = "summer #{SecureRandom.hex(4)}"
        tag1 = create(:tag, name: tag1_name, color: "#blue")
        tag2 = create(:tag, name: tag2_name, color: "#yellow")
        @inventory_item.tags << [ tag1, tag2 ]

        serialized = @serializer.as_json
        tags = serialized[:tags]

        assert_equal 2, tags.length
        assert_includes tags.map { |t| t[:name] }, tag1_name
        assert_includes tags.map { |t| t[:name] }, tag2_name
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

      test "should generate valid image URLs when image is attached" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        serialized = @serializer.as_json
        primary_image = serialized[:images][:primary]
        urls = primary_image[:urls]

        # URLs should be present and valid
        assert_not_nil urls[:original], "Original URL should be generated"
        assert_not_nil urls[:thumb], "Thumb URL should be generated"
        assert_not_nil urls[:medium], "Medium URL should be generated"
        assert_not_nil urls[:large], "Large URL should be generated"

        # URLs should be strings
        assert_kind_of String, urls[:original] if urls[:original]
        assert_kind_of String, urls[:thumb] if urls[:thumb]
        assert_kind_of String, urls[:medium] if urls[:medium]
        assert_kind_of String, urls[:large] if urls[:large]

        # URLs should contain valid format (either absolute URLs or relative paths)
        if urls[:original]
          assert_match(/^(http|https|\/)/, urls[:original], "Original URL should be valid")
        end
        if urls[:thumb]
          assert_match(/^(http|https|\/)/, urls[:thumb], "Thumb URL should be valid")
        end
      end

      test "should handle URL generation errors gracefully" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        # Mock url_for to raise an error
        @serializer.stubs(:url_for).raises(StandardError.new("URL generation failed"))

        # Should not raise, but return nil URLs
        serialized = @serializer.as_json
        primary_image = serialized[:images][:primary]

        # Should still return structure with nil URLs
        assert_not_nil primary_image
        assert_includes primary_image.keys, :urls
        urls = primary_image[:urls]
        # URLs might be nil if generation fails, which is acceptable
        assert_not_nil urls
      end

      test "should return nil URLs structure when image attachment fails" do
        # Create item without image
        item_without_image = create(:inventory_item, :clothing, user: @user)
        serializer = InventoryItemSerializer.new(item_without_image)

        serialized = serializer.as_json
        primary_image = serialized[:images][:primary]

        assert_nil primary_image, "Primary image should be nil when not attached"
      end
    end
  end
end
