class Outfit < ApplicationRecord
  include Cacheable

  belongs_to :user

  has_many :outfit_items, dependent: :destroy
  has_many :inventory_items, through: :outfit_items
  has_many :ai_analyses, dependent: :destroy

  validates :name, presence: true
  # Note: Outfits can exist without items initially (e.g., draft outfits)
  # Items can be added later through outfit_items
  # validate :must_have_at_least_one_item

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

  # Public methods used by controllers for completeness analysis
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
    colors = inventory_items.map do |item|
      # Try store_accessor first (preferred), then dig from metadata hash, then metadata string
      if item.respond_to?(:color) && item.color.present?
        item.color
      elsif item.metadata.is_a?(Hash)
        item.metadata.dig("color")
      elsif item.metadata.is_a?(String)
        parsed = JSON.parse(item.metadata) rescue {}
        parsed.dig("color")
      end
    end.compact
    colors.length >= 2 && colors.uniq.length <= 3 # Basic color coordination check
  end

  private

  def must_have_at_least_one_item
    # Only validate on create - allow updates without items (e.g., updating name, favorite status)
    # This allows outfits to be created/updated without items initially, but items should be added eventually
    if new_record? && inventory_items.empty? && outfit_items.empty?
      errors.add(:inventory_items, "must have at least one item")
    end
  end
end
