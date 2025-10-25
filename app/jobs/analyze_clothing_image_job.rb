class AnalyzeClothingImageJob < ApplicationJob
  queue_as :default
  
  def perform(inventory_item_id)
    inventory_item = InventoryItem.find(inventory_item_id)
    
    # Generate AI analysis
    analysis = analyze_item(inventory_item)
    
    # Generate vector embedding
    embedding = generate_embedding(inventory_item)
    
    # Store both analysis and vector in PostgreSQL
    inventory_item.update!(
      embedding_vector: embedding
    )
    
    inventory_item.ai_analyses.create!(
      analysis_type: :visual_analysis,
      analysis_data: analysis,
      confidence_score: analysis['confidence'] || 0.8
    )
    
    Rails.logger.info "Analysis completed for inventory item #{inventory_item_id}"
  rescue StandardError => e
    Rails.logger.error "Failed to analyze inventory item #{inventory_item_id}: #{e.message}"
    raise e
  end
  
  private
  
  def analyze_item(inventory_item)
    # Use existing Ollama service for analysis
    # This would integrate with your existing Ollama::InventoryAnalyzer
    {
      'item_type' => inventory_item.item_type,
      'colors' => extract_colors(inventory_item),
      'style' => analyze_style(inventory_item),
      'confidence' => 0.85
    }
  end
  
  def generate_embedding(inventory_item)
    # Use the new embedding generator
    Ollama::EmbeddingGenerator.generate_item_embedding(inventory_item)
  end
  
  def extract_colors(inventory_item)
    # Placeholder for color extraction
    [inventory_item.color].compact
  end
  
  def analyze_style(inventory_item)
    # Placeholder for style analysis
    inventory_item.metadata_summary[:occasion] || 'casual'
  end
end
