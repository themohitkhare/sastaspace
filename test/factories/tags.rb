# Tag factory for testing
FactoryBot.define do
  factory :tag do
    sequence(:name) { |n| "#{Faker::Commerce.material} #{n} #{SecureRandom.hex(4)}" }
    color { Faker::Color.hex_color }
  end
end
