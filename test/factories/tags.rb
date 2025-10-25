# Tag factory for testing
FactoryBot.define do
  factory :tag do
    name { Faker::Commerce.material }
    color { Faker::Color.hex_color }
  end
end
