# Category factory for testing
FactoryBot.define do
  factory :category do
    sequence(:name) { |n| "#{Faker::Commerce.department} #{SecureRandom.hex(4)} #{n}" }
    description { Faker::Lorem.sentence }
    sort_order { 1 }
    active { true }

    trait :clothing do
      sequence(:name) { |n| "#{%w[Tops Bottoms Dresses Outerwear Undergarments].sample} #{SecureRandom.hex(4)} #{n}" }
    end

    trait :shoes do
      sequence(:name) { |n| "#{%w[Athletic Dress Shoes Casual Boots].sample} #{SecureRandom.hex(4)} #{n}" }
    end

    trait :accessories do
      sequence(:name) { |n| "#{%w[Bags Belts Hats Scarves Sunglasses].sample} #{SecureRandom.hex(4)} #{n}" }
    end

    trait :jewelry do
      sequence(:name) { |n| "#{%w[Necklaces Rings Earrings Bracelets Watches].sample} #{SecureRandom.hex(4)} #{n}" }
    end
  end
end
