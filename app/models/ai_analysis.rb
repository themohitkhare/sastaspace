class AiAnalysis < ApplicationRecord
  # Associations
  belongs_to :inventory_item
  belongs_to :user

  # Validations
  validates :analysis_type, presence: true
  validates :confidence_score, presence: true
  validates :analysis_data, presence: true

  # Analysis types
  enum :analysis_type, {
    visual_analysis: "visual_analysis",
    style_analysis: "style_analysis",
    recommendation: "recommendation",
    quality_assessment: "quality_assessment"
  }

  # Scopes
  scope :recent, -> { order(created_at: :desc) }
  scope :high_confidence, -> { where(high_confidence: true) }

  # Accessors for structured analysis data
  def analysis_data_hash
    analysis_data.is_a?(Hash) ? analysis_data : {}
  end

  def item_type
    analysis_data_hash["item_type"]
  end

  def colors
    analysis_data_hash["colors"] || []
  end

  def style
    analysis_data_hash["style"]
  end

  def material
    analysis_data_hash["material"]
  end

  def brand_suggestion
    analysis_data_hash["brand_suggestion"]
  end

  def category_suggestion
    analysis_data_hash["category_suggestion"]
  end
end

