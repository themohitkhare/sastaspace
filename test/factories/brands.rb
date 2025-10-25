# Brand factory for testing
FactoryBot.define do
  factory :brand do
    name { Faker::Company.name }
    description { Faker::Lorem.sentence }
  end
end
