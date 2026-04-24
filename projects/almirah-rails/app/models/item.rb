# frozen_string_literal: true

# project_almirah.items — one row per wardrobe item.
# See migration 20260424010002_create_items.rb for the full schema.
class Item < ApplicationRecord
  self.table_name = "project_almirah.items"
  self.primary_key = "id"

  belongs_to :user

  has_many :outfit_items, foreign_key: "item_id", dependent: :destroy
  has_many :outfits, through: :outfit_items
  has_many :wear_events, foreign_key: "item_id", dependent: :destroy

  KINDS = %w[kurta saree blouse dupatta sherwani shirt jeans lehenga juttis jacket].freeze
  RACKS = %w[ethnic office weekend].freeze
  TONES = %w[cream indigo warm ink red olive rose navy sand green denim].freeze

  validates :kind,  inclusion: { in: KINDS }
  validates :rack,  inclusion: { in: RACKS }
  validates :name,  presence: true
  validates :tone,  presence: true

  scope :by_rack, ->(rack) { where(rack: rack).order(:id) }
  scope :ethnic,  -> { by_rack("ethnic") }
  scope :office,  -> { by_rack("office") }
  scope :weekend, -> { by_rack("weekend") }
  scope :in_rotation, -> { where("last_worn_at > ?", 90.days.ago) }

  # Tone → tonal background colour used in the item card.
  # Must stay in sync with the JS TONE_BG map in items.ts.
  TONE_BG = {
    "cream"  => "#f5f1e8",
    "indigo" => "#dde0ee",
    "warm"   => "#f5ebe0",
    "ink"    => "#dcdad6",
    "red"    => "#f5ddd8",
    "olive"  => "#e2e8da",
    "rose"   => "#f5dde8",
    "navy"   => "#d8dde8",
    "sand"   => "#ede8da",
    "green"  => "#dae8dd",
    "denim"  => "#d8e2ee",
  }.freeze

  TONE_SWATCH = {
    "cream"  => "#c8b99a",
    "indigo" => "#5c6bc0",
    "warm"   => "#d08060",
    "ink"    => "#888076",
    "red"    => "#c55040",
    "olive"  => "#6b7a50",
    "rose"   => "#c06080",
    "navy"   => "#3a4878",
    "sand"   => "#b0a080",
    "green"  => "#4a7858",
    "denim"  => "#4060a0",
  }.freeze

  def tone_bg
    TONE_BG.fetch(tone, "#f5f1e8")
  end

  def tone_swatch
    TONE_SWATCH.fetch(tone, "#a8a196")
  end

  def in_rotation?
    last_worn_at.present? && last_worn_at > 90.days.ago
  end

  def formatted_price
    return nil unless price_inr
    "₹#{price_inr.to_s.reverse.scan(/.{1,3}/).join(',').reverse}"
  end

  def last_worn_ago
    return "never" unless last_worn_at
    distance = (Time.current - last_worn_at).to_i
    case distance
    when 0..86_400        then "today"
    when 86_401..172_800  then "1d"
    when 172_801..604_800 then "#{(distance / 86_400).round}d"
    when 604_801..2_592_000 then "#{(distance / 604_800).round}w"
    when 2_592_001..31_536_000 then "#{(distance / 2_592_000).round}mo"
    else "#{(distance / 31_536_000).round}y"
    end
  end
end
