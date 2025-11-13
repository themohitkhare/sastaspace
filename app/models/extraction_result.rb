class ExtractionResult < ApplicationRecord
  # Associations
  belongs_to :clothing_analysis

  # Validations
  validates :status, presence: true
  validates :extraction_quality, numericality: { in: 0.0..1.0 }, allow_nil: true

  # Status enum
  enum :status, {
    pending: "pending",
    processing: "processing",
    completed: "completed",
    failed: "failed"
  }, default: "pending"

  # Scopes
  scope :successful, -> { where(status: "completed") }
  scope :failed, -> { where(status: "failed") }
  scope :pending_or_processing, -> { where(status: %w[pending processing]) }

  # Accessors for structured item data
  def item_data_hash
    item_data.is_a?(Hash) ? item_data : {}
  end

  def item_name
    item_data_hash["item_name"] || item_data_hash[:item_name] || "Unknown Item"
  end

  def item_id
    item_data_hash["id"] || item_data_hash[:id]
  end

  def extracted_image_blob
    @extracted_image_blob ||= ActiveStorage::Blob.find_by(id: extracted_image_blob_id) if extracted_image_blob_id.present?
  end

  def extraction_successful?
    # Status must be completed and blob ID must be present
    status == "completed" && extracted_image_blob_id.present?
  end
end
