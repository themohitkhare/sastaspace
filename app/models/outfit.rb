class Outfit < ApplicationRecord
  belongs_to :user

  has_many :outfit_items, dependent: :destroy
  has_many :inventory_items, through: :outfit_items

  validates :name, presence: true
  validate :must_have_at_least_one_item

  # Outfit metadata
  # Note: occasion and season are stored as direct columns, not in metadata
  store_accessor :metadata, :weather, :formality_level,
                 :color_scheme, :style_notes, :created_for_date

  enum :status, { draft: 0, active: 1, archived: 2, favorite: 3 }

  # Scopes
  scope :favorites, -> { 
    base = all
    base.where(is_favorite: true).or(base.where(status: :favorite))
  }
  scope :by_occasion, ->(occasion) { where(occasion: occasion) }
  scope :by_season, ->(season) { where(season: season) }

  # Outfit completeness scoring
  def completeness_score
    score = 0
    score += 40 if has_clothing_item?
    score += 20 if has_shoes?
    score += 20 if has_accessories?
    score += 20 if has_coordinated_colors?
    score
  end

  def complete?
    completeness_score >= 80
  end

  def worn_count
    outfit_items.sum(:worn_count) || 0
  end

  def last_worn_at
    outfit_items.maximum(:last_worn_at)
  end

  private

  def must_have_at_least_one_item
    # Only validate if outfit is persisted (not new) and has no items
    if persisted? && inventory_items.empty? && outfit_items.empty?
      errors.add(:inventory_items, "must have at least one item")
    end
  end

  def has_clothing_item?
    inventory_items.any? { |item| item.item_type == "clothing" }
  end

  def has_shoes?
    inventory_items.any? { |item| item.item_type == "shoes" }
  end

  def has_accessories?
    inventory_items.any? { |item| %w[accessories jewelry].include?(item.item_type) }
  end

  def has_coordinated_colors?
    colors = inventory_items.map { |item| item.metadata&.dig("color") || item.color }.compact
    colors.length >= 2 && colors.uniq.length <= 3 # Basic color coordination check
  end
end
