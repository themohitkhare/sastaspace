# Clothing items factories for testing
FactoryBot.define do
  factory :clothing_item do
    user
    name { Faker::Commerce.product_name }
    category { %w[top bottom dress shoes accessories outerwear].sample }
    brand { Faker::Company.name }
    color { Faker::Color.color_name }
    size { %w[XS S M L XL XXL].sample }
    season { %w[spring summer fall winter all_season].sample }
    occasion { %w[casual formal work party sport].sample }
    purchase_date { Faker::Date.between(from: 2.years.ago, to: Date.current) }
    price { Faker::Commerce.price(range: 10.0..500.0) }
    notes { Faker::Lorem.paragraph }

    trait :with_photo do
      after(:build) do |item|
        item.photo.attach(
          io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
          filename: "sample_image.jpg",
          content_type: "image/jpeg"
        )
      end
    end

    trait :summer do
      season { "summer" }
    end

    trait :winter do
      season { "winter" }
    end

    trait :casual do
      occasion { "casual" }
    end

    trait :formal do
      occasion { "formal" }
    end
  end

  factory :ai_analysis do
    user
    clothing_item
    analysis_type { "image_description" }
    prompt_used { "Describe this clothing item in detail" }
    response { Faker::Lorem.paragraph }
    confidence_score { Faker::Number.between(from: 0.0, to: 1.0) }
    processing_time_ms { Faker::Number.between(from: 100, to: 5000) }
    model_used { "llava" }
    image_hash { Digest::SHA256.hexdigest("sample_image_data") }
    high_confidence { false }

    trait :high_confidence do
      confidence_score { Faker::Number.between(from: 0.8, to: 1.0) }
      high_confidence { true }
    end

    trait :low_confidence do
      confidence_score { Faker::Number.between(from: 0.0, to: 0.5) }
      high_confidence { false }
    end
  end
end
