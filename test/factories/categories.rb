# Category factory for testing
FactoryBot.define do
  factory :category do
    name { Faker::Commerce.department }
    description { Faker::Lorem.sentence }
    sort_order { 1 }
    active { true }

    trait :clothing do
      name { %w[Tops Bottoms Dresses Outerwear Undergarments].sample }
    end

    trait :shoes do
      name { %w[Athletic Dress Shoes Casual Boots].sample }
    end

    trait :accessories do
      name { %w[Bags Belts Hats Scarves Sunglasses].sample }
    end

    trait :jewelry do
      name { %w[Necklaces Rings Earrings Bracelets Watches].sample }
    end
  end
end
