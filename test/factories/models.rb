# Model factory for testing
FactoryBot.define do
  factory :model do
    sequence(:name) { |n| "gpt-4o-mini-#{n}" }
    provider { "openai" }
    model_id { name }
    context_window { 128_000 }
    family { "gpt-4" }
  end
end
