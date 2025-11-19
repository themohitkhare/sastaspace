class InventoryItem < ApplicationRecord
  include Searchable
  include ImageProcessable
  include TypeDerivable
  include Cacheable

  belongs_to :user
  belongs_to :category
  belongs_to :subcategory, class_name: "Category", optional: true
  belongs_to :brand, optional: true
  belongs_to :clothing_analysis, optional: true

  has_one_attached :primary_image
  has_many_attached :additional_images

  has_many :ai_analyses, dependent: :destroy, class_name: "AiAnalysis"
  has_many :inventory_tags, dependent: :destroy
  has_many :tags, through: :inventory_tags

  # Core validations
  validates :name, presence: true
  validates :category, presence: true

  # Flexible metadata as JSON
  store_accessor :metadata, :color, :size, :material, :season, :occasion,
                 :care_instructions, :fit_notes, :style_notes, :gender_styling,
                 :pattern_type, :pattern_details, :style_category

  # Derive coarse type from category hierarchy instead of storing item_type column

  # Status tracking
  enum :status, { active: 0, archived: 1, donated: 2, sold: 3 }

  # Scopes for filtering
  # Use category hierarchy for type-like filtering (top-level category name)
  scope :by_type, ->(type) {
    t = type.to_s.downcase
    patterns = {
      "clothing" => %w[tops bottoms dresses outerwear undergarments shirts pants t-shirts sweaters jackets coats jeans skirts],
      "shoes" => %w[athletic dress shoes casual boots sneakers loafers sandals running training oxfords heels],
      "accessories" => %w[bags belts hats scarves sunglasses clutches totes backpacks beanies fedoras],
      "jewelry" => %w[necklaces rings earrings bracelets watches]
    }
    like_clauses = (patterns[t] || []).map { |p| "LOWER(categories.name) LIKE '#{p}%'" }
    if like_clauses.empty?
      where("1=0") # Return empty result for unknown types
    else
      joins(:category).where(like_clauses.join(" OR "))
    end
  }
  scope :by_category, ->(category) { joins(:category).where(categories: { name: category }) }
  scope :by_season, ->(season) { where("metadata->>'season' = ?", season) }
  scope :by_color, ->(color) { where("metadata->>'color' LIKE ?", "%#{color}%") }
  scope :by_brand, ->(brand) { joins(:brand).where(brands: { name: brand }) }
  scope :recently_worn, -> { where.not(last_worn_at: nil).order(last_worn_at: :desc) }
  scope :never_worn, -> { where(last_worn_at: nil) }
  scope :most_worn, -> { reorder(wear_count: :desc, created_at: :desc) }
  scope :without_stock_photo_extraction, -> { where(stock_photo_extraction_completed_at: nil) }

  # Type-specific validations
  validate :validate_type_specific_fields
  validate :validate_item_type_presence

  def increment_wear_count!
    increment!(:wear_count)
    update!(last_worn_at: Time.current)
  end

  def metadata_summary
    {
      color: color,
      size: size,
      material: material,
      season: season,
      occasion: occasion
    }.compact
  end

  private

  def validate_type_specific_fields
    ItemValidationService.validate_type_specific_fields(self)
  end

  def validate_item_type_presence
    ItemValidationService.validate_item_type_presence(self)
  end
end
