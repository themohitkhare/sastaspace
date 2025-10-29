# Category factory for testing
FactoryBot.define do
  factory :category do
    sequence(:name) { |n| "#{Faker::Commerce.department} #{n}" }
    description { Faker::Lorem.sentence }
    sort_order { 1 }
    active { true }

    trait :clothing do
      sequence(:name) { |n| "#{%w[Tops Bottoms Dresses Outerwear Undergarments].sample} #{n}" }
    end

    trait :shoes do
      sequence(:name) { |n| "#{%w[Athletic Dress Shoes Casual Boots].sample} #{n}" }
    end

    trait :accessories do
      sequence(:name) { |n| "#{%w[Bags Belts Hats Scarves Sunglasses].sample} #{n}" }
    end

    trait :jewelry do
      sequence(:name) { |n| "#{%w[Necklaces Rings Earrings Bracelets Watches].sample} #{n}" }
    end
  end
end
