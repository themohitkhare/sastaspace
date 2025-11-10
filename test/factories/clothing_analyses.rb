FactoryBot.define do
  factory :clothing_analysis do
    user
    image_blob_id { ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    ).id }
    parsed_data do
      {
        "total_items_detected" => 2,
        "people_count" => 1,
        "items" => [
          {
            "id" => "item_001",
            "item_name" => "Blue Shirt",
            "category" => "tops",
            "subcategory" => "shirt",
            "color_primary" => "blue",
            "pattern_type" => "solid",
            "material_type" => "cotton",
            "style_category" => "casual",
            "gender_styling" => "men",
            "extraction_priority" => "high",
            "confidence" => 0.9
          },
          {
            "id" => "item_002",
            "item_name" => "Black Jeans",
            "category" => "bottoms",
            "subcategory" => "jeans",
            "color_primary" => "black",
            "pattern_type" => "solid",
            "material_type" => "denim",
            "style_category" => "casual",
            "gender_styling" => "unisex",
            "extraction_priority" => "medium",
            "confidence" => 0.85
          }
        ]
      }
    end
    items_detected { 2 }
    confidence { 0.875 }
    status { "completed" }

    trait :with_men_items do
      parsed_data do
        {
          "total_items_detected" => 1,
          "people_count" => 1,
          "items" => [
            {
              "id" => "item_001",
              "item_name" => "Men's Suit",
              "category" => "outerwear",
              "gender_styling" => "men",
              "confidence" => 0.95
            }
          ]
        }
      end
      items_detected { 1 }
    end

    trait :with_women_items do
      parsed_data do
        {
          "total_items_detected" => 1,
          "people_count" => 1,
          "items" => [
            {
              "id" => "item_001",
              "item_name" => "Women's Dress",
              "category" => "dresses",
              "gender_styling" => "women",
              "confidence" => 0.92
            }
          ]
        }
      end
      items_detected { 1 }
    end

    trait :with_unisex_items do
      parsed_data do
        {
          "total_items_detected" => 1,
          "people_count" => 1,
          "items" => [
            {
              "id" => "item_001",
              "item_name" => "Hoodie",
              "category" => "outerwear",
              "gender_styling" => "unisex",
              "confidence" => 0.88
            }
          ]
        }
      end
      items_detected { 1 }
    end

    trait :failed do
      status { "failed" }
      parsed_data { { "error" => "Analysis failed" } }
      items_detected { 0 }
      confidence { nil }
    end
  end
end
