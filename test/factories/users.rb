# User factory for testing
FactoryBot.define do
  factory :user do
    email { Faker::Internet.unique.email }
    password { "Password123!" }
    password_confirmation { "Password123!" }
    first_name { Faker::Name.first_name }
    last_name { Faker::Name.last_name }

    trait :with_profile do
      after(:create) do |user|
        create(:user_profile, user: user)
      end
    end

    trait :confirmed do
      confirmed_at { Time.current }
    end
  end

  factory :user_profile do
    user
    bio { Faker::Lorem.paragraph }
    location { Faker::Address.city }
    website { Faker::Internet.url }
  end
end
