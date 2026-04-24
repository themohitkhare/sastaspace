# frozen_string_literal: true

class WearEvent < ApplicationRecord
  self.table_name = "project_almirah.wear_events"
  self.primary_key = "id"

  belongs_to :item, foreign_key: "item_id"

  validates :worn_at, presence: true

  scope :recent, -> { order(worn_at: :desc) }
  scope :for_attendee, ->(name) { where("? = ANY(attendees)", name) }
end
