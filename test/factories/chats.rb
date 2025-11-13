# Chat factory for testing
FactoryBot.define do
  factory :chat do
    association :user
    association :model
  end
end
