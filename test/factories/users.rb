# User factory for testing
FactoryBot.define do
  factory :user do
    email { Faker::Internet.unique.email }
    password { "Password123!" }
    password_confirmation { "Password123!" }
    first_name { Faker::Name.first_name }
    last_name { Faker::Name.last_name }

    trait :confirmed do
      confirmed_at { Time.current }
    end
  end
end
