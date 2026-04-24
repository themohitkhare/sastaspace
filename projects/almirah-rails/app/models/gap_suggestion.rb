# frozen_string_literal: true

class GapSuggestion < ApplicationRecord
  self.table_name = "project_almirah.gap_suggestions"
  self.primary_key = "id"

  SOURCES = %w[Myntra Ajio Amazon].freeze

  validates :kind,  presence: true
  validates :name,  presence: true
  validates :tone,  presence: true
  validates :reason, presence: true
  validates :source, inclusion: { in: SOURCES }
  validates :price_inr, numericality: { greater_than_or_equal_to: 0 }
  validates :url,  presence: true

  def tone_bg
    Item::TONE_BG.fetch(tone, "#f5f1e8")
  end

  def formatted_price
    "₹#{price_inr.to_s.reverse.scan(/.{1,3}/).join(',').reverse}"
  end
end
