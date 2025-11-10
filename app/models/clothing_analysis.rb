class ClothingAnalysis < ApplicationRecord
  # Associations
  belongs_to :user
  has_many :inventory_items, dependent: :nullify

  # Validations
  validates :image_blob_id, presence: true
  validates :status, presence: true
  validates :items_detected, numericality: { greater_than_or_equal_to: 0 }
  validates :confidence, numericality: { in: 0.0..1.0 }, allow_nil: true

  # Status enum
  enum :status, {
    pending: "pending",
    processing: "processing",
    completed: "completed",
    failed: "failed"
  }, default: "completed"

  # Scopes
  scope :recent, -> { order(created_at: :desc) }
  scope :high_confidence, -> { where("confidence >= ?", 0.7) }
  scope :with_items, -> { where("items_detected > 0") }

  # Accessors for structured parsed data
  def parsed_data_hash
    parsed_data.is_a?(Hash) ? parsed_data : {}
  end

  def total_items_detected
    parsed_data_hash["total_items_detected"] || items_detected || 0
  end

  def people_count
    parsed_data_hash["people_count"] || 0
  end

  def items
    parsed_data_hash["items"] || []
  end

  def image_blob
    @image_blob ||= ActiveStorage::Blob.find_by(id: image_blob_id)
  end

  # Calculate average confidence from items if available
  def calculate_average_confidence
    items_array = items
    return confidence if items_array.empty?

    confidences = items_array.map { |item| item["confidence"] || 0.0 }.compact
    return confidence if confidences.empty?

    (confidences.sum.to_f / confidences.length).round(2)
  end
end
