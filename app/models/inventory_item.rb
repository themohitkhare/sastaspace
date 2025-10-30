class InventoryItem < ApplicationRecord
  belongs_to :user
  belongs_to :category
  belongs_to :subcategory, class_name: "Category", optional: true
  belongs_to :brand, optional: true

  has_one_attached :primary_image
  has_many_attached :additional_images

  has_many :ai_analyses, dependent: :destroy, class_name: "AiAnalysis"
  has_many :inventory_tags, dependent: :destroy
  has_many :tags, through: :inventory_tags

  # Vector search capabilities - using Rails scopes with Arel.sql
  def similar_items(limit: 5)
    return [] unless embedding_vector.present?

    vector_str = "[#{embedding_vector.join(',')}]"

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(id: id)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> '#{vector_str}'::vector"))
        .limit(limit)
  end

  def find_similar_items(limit: 10)
    return [] unless embedding_vector.present?

    vector_str = "[#{embedding_vector.join(',')}]"

    user.inventory_items
        .includes(:category, :brand, :tags,
                  primary_image_attachment: :blob,
                  additional_images_attachments: :blob)
        .where.not(id: id)
        .where.not(embedding_vector: nil)
        .order(Arel.sql("embedding_vector <-> '#{vector_str}'::vector"))
        .limit(limit)
  end

  # Scope-based approach for direct vector search
  scope :similar_to, ->(vector, limit: 10) {
    vector_str = "[#{vector.join(',')}]"
    where.not(embedding_vector: nil)
         .order(Arel.sql("embedding_vector <-> '#{vector_str}'::vector"))
         .limit(limit)
  }

  # Core validations
  validates :name, presence: true
  validates :category, presence: true

  # Flexible metadata as JSON
  store_accessor :metadata, :color, :size, :material, :season, :occasion,
                 :care_instructions, :fit_notes, :style_notes

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
    joins(:category).where(like_clauses.join(" OR "))
  }
  scope :by_category, ->(category) { joins(:category).where(categories: { name: category }) }
  scope :by_season, ->(season) { where("metadata->>'season' = ?", season) }
  scope :by_color, ->(color) { where("metadata->>'color' LIKE ?", "%#{color}%") }
  scope :by_brand, ->(brand) { joins(:brand).where(brands: { name: brand }) }
  scope :recently_worn, -> { where.not(last_worn_at: nil).order(last_worn_at: :desc) }
  scope :never_worn, -> { where(last_worn_at: nil) }
  scope :most_worn, -> { reorder(wear_count: :desc, created_at: :desc) }

  # Type-specific validations
  validate :validate_type_specific_fields
  validate :validate_item_type_presence

  # Image validations
  validate :validate_primary_image_content_type
  validate :validate_primary_image_size
  validate :validate_additional_images_content_type
  validate :validate_additional_images_size

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

  # Image variants for different use cases
  def primary_image_variants
    return {} unless primary_image.attached?

    {
      thumb: primary_image.variant(resize_to_limit: [ 150, 150 ]),
      medium: primary_image.variant(resize_to_limit: [ 400, 400 ]),
      large: primary_image.variant(resize_to_limit: [ 800, 800 ])
    }
  end

  def additional_image_variants(image)
    return {} if image.nil? || (image.respond_to?(:attached?) && !image.attached?)

    {
      thumb: image.variant(resize_to_limit: [ 150, 150 ]),
      medium: image.variant(resize_to_limit: [ 400, 400 ]),
      large: image.variant(resize_to_limit: [ 800, 800 ])
    }
  end

  # Security: Strip EXIF data and process images
  after_create_commit :process_images
  after_update_commit :process_images

  # Backward-compatibility for legacy tests/serializers expecting `item_type`
  def item_type
    # If explicitly overridden to nil, honor that (used by tests)
    if defined?(@item_type_overridden) && @item_type_overridden && @virtual_item_type.nil?
      return nil
    end
    return @virtual_item_type if @virtual_item_type.present?
    top_level_category
  end

  # Writer is a no-op retained for compatibility to avoid NoMethodError in tests
  def item_type=(value)
    @item_type_overridden = true
    @virtual_item_type = value.presence
  end

  private

  def process_images
    if primary_image.attached?
      ImageProcessingJob.perform_later(self)
    end
    additional_images.each do |image|
      if image.present?
        ImageProcessingJob.perform_later(self, image.id)
      end
    end
  end

  def validate_type_specific_fields
    case item_type
    when "clothing"
      validate_clothing_fields
    when "shoes"
      validate_shoes_fields
    when "accessories"
      validate_accessories_fields
    when "jewelry"
      validate_jewelry_fields
    end
  end

  # Ensure virtual `item_type` (derived or overridden) is present
  def validate_item_type_presence
    errors.add(:item_type, "can't be blank") if item_type.blank?
  end

  def validate_clothing_fields
    # Clothing-specific validations
    if size.present? && !valid_clothing_size?
      errors.add(:size, "is not a valid clothing size")
    end
  end

  def validate_shoes_fields
    # Shoes-specific validations
    if size.present? && !valid_shoe_size?
      errors.add(:size, "is not a valid shoe size")
    end
  end

  def validate_accessories_fields
    # Accessories-specific validations
  end

  def validate_jewelry_fields
    # Jewelry-specific validations
  end

  def valid_clothing_size?
    # Basic clothing size validation
    %w[XS S M L XL XXL].include?(size) || size.match?(/\d+/)
  end

  def valid_shoe_size?
    # Basic shoe size validation
    size.match?(/\d+(\.\d+)?/) && size.to_f.between?(3, 15)
  end

  def top_level_category
    node = category
    return nil unless node
    if node.respond_to?(:parent_id) && node.parent_id.present?
      while node.parent_id.present?
        node = node.respond_to?(:parent_category) ? node.parent_category : node.parent
      end
      return node.name.to_s.downcase
    end
    category_type_from_name(node.name)
  end


  def validate_primary_image_content_type
    return unless primary_image.attached?

    allowed_types = %w[image/jpeg image/jpg image/png image/webp]
    unless allowed_types.include?(primary_image.content_type)
      errors.add(:primary_image, "is not a valid content type")
    end
  end

  def validate_primary_image_size
    return unless primary_image.attached?

    max_size = 5.megabytes
    if primary_image.byte_size > max_size
      errors.add(:primary_image, "is too large")
    end
  end

  def validate_additional_images_content_type
    return unless additional_images.attached?

    allowed_types = %w[image/jpeg image/jpg image/png image/webp]
    additional_images.each do |image|
      unless allowed_types.include?(image.content_type)
        errors.add(:additional_images, "is not a valid content type")
        break
      end
    end
  end

  def validate_additional_images_size
    return unless additional_images.attached?

    max_size = 5.megabytes
    additional_images.each do |image|
      if image.byte_size > max_size
        errors.add(:additional_images, "is too large")
        break
      end
    end
  end

  def category_type_from_name(name)
    down = name.to_s.downcase
    return "clothing" if %w[tops bottoms dresses outerwear undergarments shirts pants t-shirts sweaters jackets coats jeans skirts].any? { |p| down.start_with?(p) }
    return "shoes" if %w[athletic dress shoes casual boots sneakers loafers sandals running training oxfords heels].any? { |p| down.start_with?(p) }
    return "accessories" if %w[bags belts hats scarves sunglasses clutches totes backpacks beanies fedoras].any? { |p| down.start_with?(p) }
    return "jewelry" if %w[necklaces rings earrings bracelets watches].any? { |p| down.start_with?(p) }
    "clothing"
  end
end
