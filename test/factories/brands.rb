# Brand factory for testing
FactoryBot.define do
  factory :brand do
    sequence(:name) { |n| "Brand #{n}-#{Faker::Company.name}" }
    description { Faker::Lorem.sentence }
  end
end
