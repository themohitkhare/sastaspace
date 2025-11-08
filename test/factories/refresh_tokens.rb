FactoryBot.define do
  factory :refresh_token do
    association :user
    token { RefreshToken.generate_token }
    expires_at { 30.days.from_now }
    blacklisted { false }
  end
end
