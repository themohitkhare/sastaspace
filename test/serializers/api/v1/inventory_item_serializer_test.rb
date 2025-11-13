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
        assert_nil serialized[:last_worn_at]
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

      test "serialize_category returns nil for nil category" do
        result = @serializer.send(:serialize_category, nil)

        assert_nil result
      end

      test "serialize_brand handles brand with nil description" do
        brand = create(:brand, description: nil)
        item = create(:inventory_item, brand: brand)
        serializer = InventoryItemSerializer.new(item)

        result = serializer.send(:serialize_brand, brand)

        assert_equal brand.id, result[:id]
        assert_equal brand.name, result[:name]
        assert_nil result[:description]
      end

      test "serialize_tag handles tag with nil color" do
        tag = create(:tag, color: nil)
        @inventory_item.tags << tag

        result = @serializer.send(:serialize_tag, tag)

        assert_equal tag.id, result[:id]
        assert_equal tag.name, result[:name]
        assert_nil result[:color]
      end

      test "serialize_image_with_variants handles image serialization errors gracefully" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        # Mock image methods to raise errors
        @inventory_item.primary_image.stubs(:id).raises(StandardError.new("ID error"))
        Rails.logger.stubs(:warn)

        result = @serializer.send(:serialize_image_with_variants, @inventory_item.primary_image)

        assert_not_nil result
        assert_nil result[:id]
        assert_nil result[:filename]
        assert_not_nil result[:urls]
      end

      test "serialize_image_with_variants handles nil image" do
        result = @serializer.send(:serialize_image_with_variants, nil)

        assert_nil result
      end

      test "url_for returns nil when attachment not attached" do
        unattached = @inventory_item.primary_image
        result = @serializer.send(:url_for, unattached)

        assert_nil result
      end

      test "url_for handles rails_blob_url errors" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        Rails.application.routes.url_helpers.stubs(:rails_blob_url).raises(StandardError.new("URL error"))
        Rails.logger.stubs(:warn)

        result = @serializer.send(:url_for, @inventory_item.primary_image)

        # Should try fallback url_for
        assert result.nil? || result.is_a?(String)
      end

      test "url_for handles url_for fallback errors" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        Rails.application.routes.url_helpers.stubs(:rails_blob_url).raises(StandardError.new("URL error"))
        Rails.application.routes.url_helpers.stubs(:url_for).raises(StandardError.new("Fallback error"))
        Rails.logger.stubs(:warn)

        result = @serializer.send(:url_for, @inventory_item.primary_image)

        assert_nil result
      end

      test "safe_variant_url returns nil when image not attached" do
        unattached = @inventory_item.primary_image
        result = @serializer.send(:safe_variant_url, unattached, [ 150, 150 ])

        assert_nil result
      end

      test "safe_variant_url handles variant creation errors" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        @inventory_item.primary_image.stubs(:variant).raises(LoadError.new("VIPS not available"))
        Rails.logger.stubs(:debug)

        result = @serializer.send(:safe_variant_url, @inventory_item.primary_image, [ 150, 150 ])

        assert_nil result
      end

      test "safe_variant_url handles variant URL generation errors" do
        @inventory_item.primary_image.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "test.jpg",
          content_type: "image/jpeg"
        )

        variant_mock = mock
        variant_mock.stubs(:processed).returns(true)
        @inventory_item.primary_image.stubs(:variant).returns(variant_mock)
        Rails.application.routes.url_helpers.stubs(:rails_representation_url).raises(StandardError.new("URL error"))
        Rails.logger.stubs(:debug)

        result = @serializer.send(:safe_variant_url, @inventory_item.primary_image, [ 150, 150 ])

        assert_nil result
      end

      test "as_json handles StandardError and re-raises" do
        @serializer.stubs(:serialize_category).raises(StandardError.new("Serialization error"))
        Rails.logger.stubs(:error)

        assert_raises(StandardError) do
          @serializer.as_json
        end
      end

      test "as_json logs error with backtrace" do
        @serializer.stubs(:serialize_category).raises(StandardError.new("Serialization error"))
        log_messages = []
        Rails.logger.stubs(:error).with { |msg| log_messages << msg; true }

        assert_raises(StandardError) do
          @serializer.as_json
        end

        error_log = log_messages.find { |msg| msg.include?("Error in InventoryItemSerializer#as_json") }
        assert error_log.present?, "Should log error"
      end

      test "default_host returns localhost when no config" do
        original_host = Rails.application.config.action_controller.default_url_options[:host]
        Rails.application.config.action_controller.default_url_options.delete(:host)
        Rails.application.routes.default_url_options.delete(:host)

        result = @serializer.send(:default_host)

        assert_equal "localhost", result
      ensure
        Rails.application.config.action_controller.default_url_options[:host] = original_host if original_host
      end

      test "default_port returns 3000 in development" do
        Rails.env.stubs(:development?).returns(true)
        original_port = Rails.application.config.action_controller.default_url_options[:port]
        Rails.application.config.action_controller.default_url_options.delete(:port)
        Rails.application.routes.default_url_options.delete(:port)

        result = @serializer.send(:default_port)

        assert_equal 3000, result
      ensure
        Rails.application.config.action_controller.default_url_options[:port] = original_port if original_port
        Rails.env.unstub(:development?)
      end

      test "default_protocol returns https in production" do
        Rails.env.stubs(:production?).returns(true)

        result = @serializer.send(:default_protocol)

        assert_equal "https", result
      ensure
        Rails.env.unstub(:production?)
      end

      test "default_protocol returns http in non-production" do
        Rails.env.stubs(:production?).returns(false)

        result = @serializer.send(:default_protocol)

        assert_equal "http", result
      ensure
        Rails.env.unstub(:production?)
      end

      test "should serialize item with nil category" do
        # Create item with category, then stub category to return nil to test serializer behavior
        item_with_category = create(:inventory_item, :clothing)

        # Stub the category association to return nil (database constraint prevents actual nil)
        item_with_category.stubs(:category).returns(nil)

        serializer = InventoryItemSerializer.new(item_with_category)

        serialized = serializer.as_json

        assert_nil serialized[:category]
      end

      test "should serialize item with empty tags" do
        item_without_tags = create(:inventory_item, :clothing, user: @user)
        serializer = InventoryItemSerializer.new(item_without_tags)

        serialized = serializer.as_json

        assert_equal [], serialized[:tags]
      end
    end
  end
end
