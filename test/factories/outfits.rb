# Outfit factory for testing
FactoryBot.define do
  factory :outfit do
    user
    sequence(:name) { |n| "Outfit #{n} #{SecureRandom.hex(4)}" }
    description { Faker::Lorem.sentence }
    occasion { %w[casual formal work party sport].sample }
    is_favorite { false }
    is_public { false }

    trait :favorite do
      is_favorite { true }
    end

    trait :public do
      is_public { true }
    end

    trait :casual do
      occasion { "casual" }
    end

    trait :formal do
      occasion { "formal" }
    end

    trait :with_items do
      after(:create) do |outfit|
        user = outfit.user
        # Create some inventory items and add them to the outfit
        category = create(:category, :clothing)
        item1 = create(:inventory_item, user: user, category: category)
        item2 = create(:inventory_item, user: user, category: category)

        outfit.outfit_items.create!(inventory_item: item1)
        outfit.outfit_items.create!(inventory_item: item2)
      end
    end
  end
end
