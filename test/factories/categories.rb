# Category factory for testing
FactoryBot.define do
  factory :category do
    name { Faker::Commerce.department }
    description { Faker::Lorem.sentence }
    
    trait :clothing do
      name { Category::CLOTHING_CATEGORIES.sample }
    end
    
    trait :shoes do
      name { Category::SHOES_CATEGORIES.sample }
    end
    
    trait :accessories do
      name { Category::ACCESSORIES_CATEGORIES.sample }
    end
    
    trait :jewelry do
      name { Category::JEWELRY_CATEGORIES.sample }
    end
  end
end
