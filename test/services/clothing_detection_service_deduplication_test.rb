require "test_helper"

# Tests for deduplication logic in ClothingDetectionService
# Added after discovering that AI models sometimes detect the same item multiple times
# with different names (e.g., "Light-Colored Patterned Dress" AND "Yellow Polo Shirt")
class ClothingDetectionServiceDeduplicationTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    image_path = Rails.root.join("test/fixtures/files/clothing_outfit_1.jpg")
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(image_path),
      filename: "clothing_outfit_1.jpg",
      content_type: "image/jpeg"
    )
    @service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: @user,
      model_name: "qwen3-vl:8b"
    )
  end

  test "deduplicate_detected_items removes exact duplicates" do
    items = [
      {
        "item_name" => "Yellow Floral Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      },
      {
        "item_name" => "Yellow Floral Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 1, result.length, "Should remove exact duplicate"
    assert_equal "Yellow Floral Shirt", result[0]["item_name"]
  end

  test "deduplicate_detected_items removes similar items with different descriptors" do
    # Real-world case: AI detected same yellow shirt with similar but different names
    items = [
      {
        "item_name" => "Yellow Floral Button-Up Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      },
      {
        "item_name" => "Yellow Floral Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 1, result.length, "Should remove similar items (one name contains the other)"
  end

  test "deduplicate_detected_items removes dress vs shirt confusion for same garment" do
    # Real-world case from production: Same yellow floral garment detected as both
    items = [
      {
        "item_name" => "Yellow Floral Dress",
        "category" => "tops",  # Incorrectly categorized
        "color_primary" => "yellow"
      },
      {
        "item_name" => "Yellow Floral Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 1, result.length, "Should deduplicate dress/shirt confusion when both in tops category"
  end

  test "deduplicate_detected_items keeps items with different categories" do
    items = [
      {
        "item_name" => "Yellow Floral Top",
        "category" => "tops",
        "color_primary" => "yellow"
      },
      {
        "item_name" => "Yellow Floral Skirt",
        "category" => "bottoms",
        "color_primary" => "yellow"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 2, result.length, "Should keep items with different categories"
  end

  test "deduplicate_detected_items keeps items with different colors" do
    items = [
      {
        "item_name" => "Floral Shirt",
        "category" => "tops",
        "color_primary" => "yellow"
      },
      {
        "item_name" => "Floral Shirt",
        "category" => "tops",
        "color_primary" => "blue"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 2, result.length, "Should keep items with different colors"
  end

  test "deduplicate_detected_items normalizes descriptive words" do
    # "Light-Colored" and "Dark-Colored" should normalize to same base name
    items = [
      {
        "item_name" => "Light-Colored Patterned Shirt",
        "category" => "tops",
        "color_primary" => "white"
      },
      {
        "item_name" => "Dark-Colored Patterned Shirt",
        "category" => "tops",
        "color_primary" => "white"
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    assert_equal 1, result.length, "Should normalize 'light-colored' and 'dark-colored' as duplicates"
  end

  test "deduplicate_detected_items handles empty array" do
    result = @service.send(:deduplicate_detected_items, [])
    assert_equal [], result
  end

  test "deduplicate_detected_items handles items with missing fields" do
    items = [
      {
        "item_name" => "Shirt"
        # Missing category and color
      },
      {
        "category" => "tops"
        # Missing name and color
      }
    ]

    result = @service.send(:deduplicate_detected_items, items)

    # Should not crash, should keep both (different signatures)
    assert_equal 2, result.length
  end

  test "validate_and_enhance_results applies deduplication" do
    results = {
      "items" => [
        {
          "item_name" => "Yellow Shirt",
          "category" => "tops",
          "color_primary" => "yellow",
          "gender_styling" => "unisex"
        },
        {
          "item_name" => "Light-Colored Patterned Yellow Shirt",
          "category" => "tops",
          "color_primary" => "yellow",
          "gender_styling" => "unisex"
        }
      ],
      "total_items_detected" => 2
    }

    enhanced = @service.send(:validate_and_enhance_results, results)

    assert_equal 1, enhanced["items"].length, "Should deduplicate similar items"
    assert_equal 1, enhanced["total_items_detected"], "Should update total count after deduplication"
  end

  test "deduplication logs when items are removed" do
    items = [
      {
        "item_name" => "Black Trousers",
        "category" => "bottoms",
        "color_primary" => "black"
      },
      {
        "item_name" => "Dark Trousers",
        "category" => "bottoms",
        "color_primary" => "black"
      }
    ]

    log_messages = []
    Rails.logger.stubs(:info).with { |msg| log_messages << msg; true }

    @service.send(:deduplicate_detected_items, items)

    assert log_messages.any? { |msg| msg.include?("DEDUPLICATION") && msg.include?("Removed") },
           "Should log deduplication activity"
  end
end
