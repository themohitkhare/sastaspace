FactoryBot.define do
  factory :extraction_result do
    clothing_analysis
    item_data do
      {
        "id" => "item_#{SecureRandom.hex(4)}",
        "item_name" => "Extracted Item",
        "category" => "tops",
        "description" => "An extracted clothing item"
      }
    end
    status { "pending" }
    extraction_quality { nil }

    trait :completed do
      status { "completed" }
      extraction_quality { 0.85 }
      extracted_image_blob_id do
        ActiveStorage::Blob.create_and_upload!(
          io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
          filename: "sample_image.jpg",
          content_type: "image/jpeg"
        ).id
      end
    end

    trait :failed do
      status { "failed" }
      extraction_quality { nil }
    end

    trait :processing do
      status { "processing" }
    end
  end
end
