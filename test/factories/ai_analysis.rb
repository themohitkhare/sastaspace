# AiAnalysis factory for testing
FactoryBot.define do
  factory :ai_analysis do
    association :inventory_item, factory: :inventory_item
    user { inventory_item.user }
    analysis_type { :visual_analysis }
    confidence_score { 0.85 }
    high_confidence { true }
    analysis_data do
      {
        item_type: "clothing",
        colors: ["blue", "white"],
        style: "casual",
        material: "cotton",
        brand_suggestion: "Nike",
        category_suggestion: "Tops"
      }
    end
    model_used { "llama3" }
    prompt_used { "Analyze this clothing item" }
    response { "This is a blue cotton t-shirt" }
    processing_time_ms { 250 }
    image_hash { SecureRandom.hex }
  end
end
