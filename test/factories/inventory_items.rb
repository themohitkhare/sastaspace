# InventoryItem factory for testing
FactoryBot.define do
  factory :inventory_item do
    user
    category
    brand
    sequence(:name) { |n| "Inventory Item #{n}" }
    item_type { InventoryItem.item_types.keys.sample }
    description { Faker::Lorem.paragraph }
    status { :active }
    purchase_price { Faker::Commerce.price(range: 10.0..500.0) }
    purchase_date { Faker::Date.between(from: 2.years.ago, to: Date.current) }
    wear_count { 0 }
    last_worn_at { nil }
    
    metadata do
      {
        color: Faker::Color.color_name,
        size: %w[XS S M L XL XXL].sample,
        material: Faker::Commerce.material,
        season: %w[spring summer fall winter].sample,
        occasion: %w[casual formal work party].sample
      }
    end
    
    trait :clothing do
      item_type { :clothing }
      association :category, factory: [:category, :clothing]
      metadata do
        {
          color: Faker::Color.color_name,
          size: %w[XS S M L XL XXL].sample,
          material: Faker::Commerce.material,
          season: %w[spring summer fall winter].sample,
          occasion: %w[casual formal work party].sample,
          care_instructions: Faker::Lorem.sentence
        }
      end
    end
    
    trait :shoes do
      item_type { :shoes }
      association :category, factory: [:category, :shoes]
      metadata do
        {
          color: Faker::Color.color_name,
          size: Faker::Number.between(from: 6, to: 12).to_s,
          material: Faker::Commerce.material,
          season: %w[spring summer fall winter].sample,
          occasion: %w[casual formal work party].sample,
          heel_height: Faker::Number.between(from: 0, to: 4).to_s
        }
      end
    end
    
    trait :accessories do
      item_type { :accessories }
      association :category, factory: [:category, :accessories]
      metadata do
        {
          color: Faker::Color.color_name,
          material: Faker::Commerce.material,
          season: %w[spring summer fall winter].sample,
          occasion: %w[casual formal work party].sample
        }
      end
    end
    
    trait :jewelry do
      item_type { :jewelry }
      association :category, factory: [:category, :jewelry]
      metadata do
        {
          color: Faker::Color.color_name,
          material: %w[gold silver platinum].sample,
          season: %w[spring summer fall winter].sample,
          occasion: %w[casual formal work party].sample,
          metal_type: %w[gold silver platinum].sample,
          stone_type: %w[diamond ruby emerald sapphire].sample
        }
      end
    end
    
    trait :with_tags do
      after(:create) do |item|
        create_list(:tag, 3).each do |tag|
          item.tags << tag
        end
      end
    end
    
    trait :never_worn do
      wear_count { 0 }
      last_worn_at { nil }
    end
    
    trait :frequently_worn do
      wear_count { Faker::Number.between(from: 20, to: 100) }
      last_worn_at { Faker::Date.between(from: 1.week.ago, to: Date.current) }
    end
  end
  
  factory :inventory_tag do
    inventory_item
    tag
  end
end
