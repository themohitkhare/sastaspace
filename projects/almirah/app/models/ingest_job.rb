# frozen_string_literal: true

class IngestJob < ApplicationRecord
  self.table_name = "project_almirah.ingest_jobs"
  self.primary_key = "id"

  belongs_to :user

  STATUSES = %w[queued processing done error].freeze

  validates :status, inclusion: { in: STATUSES }

  scope :for_user, ->(user) { where(user_id: user.id) }
  scope :pending,  -> { where(status: %w[queued processing]) }
  scope :complete, -> { where(status: %w[done error]) }

  def queued?    = status == "queued"
  def processing? = status == "processing"
  def done?      = status == "done"
  def error?     = status == "error"

  def progress_fraction
    return 0.0 if photo_count.zero?
    return 1.0 if done?
    # No per-photo progress row — fake a steady march while processing.
    0.5
  end
end
