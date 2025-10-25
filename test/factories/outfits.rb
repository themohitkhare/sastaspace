# Outfit factories for testing
FactoryBot.define do
  factory :outfit do
    user
    name { Faker::Commerce.product_name + " Outfit" }
    description { Faker::Lorem.paragraph }
    occasion { %w[casual formal work party sport date].sample }
    season { %w[spring summer fall winter all_season].sample }
    weather_condition { %w[sunny cloudy rainy snowy].sample }
    temperature_range { "#{Faker::Number.between(from: 10, to: 30)}-#{Faker::Number.between(from: 30, to: 40)}°C" }
    is_favorite { false }
    is_public { false }

    trait :casual do
      occasion { "casual" }
    end

    trait :formal do
      occasion { "formal" }
    end

    trait :summer do
      season { "summer" }
    end

    trait :winter do
      season { "winter" }
    end

    trait :favorite do
      is_favorite { true }
    end

    trait :public do
      is_public { true }
    end

    trait :with_items do
      after(:create) do |outfit|
        # Add 3-5 random clothing items
        items = create_list(:clothing_item, rand(3..5), user: outfit.user)
        items.each do |item|
          create(:outfit_item, outfit: outfit, clothing_item: item)
        end
      end
    end
  end

  factory :outfit_item do
    outfit
    clothing_item
    position { Faker::Number.between(from: 1, to: 10) }
    notes { Faker::Lorem.sentence }

    trait :top do
      association :clothing_item, category: "top"
    end

    trait :bottom do
      association :clothing_item, category: "bottom"
    end

    trait :shoes do
      association :clothing_item, category: "shoes"
    end

    trait :accessories do
      association :clothing_item, category: "accessories"
    end
  end
end
