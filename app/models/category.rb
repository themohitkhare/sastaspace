class Category < ApplicationRecord
  validates :name, presence: true, uniqueness: true
  
  has_many :inventory_items, dependent: :restrict_with_error
  
  # Predefined categories for different item types
  CLOTHING_CATEGORIES = %w[tops bottoms dresses outerwear undergarments].freeze
  SHOES_CATEGORIES = %w[sneakers heels boots sandals flats].freeze
  ACCESSORIES_CATEGORIES = %w[bags belts hats scarves sunglasses].freeze
  JEWELRY_CATEGORIES = %w[necklaces rings earrings bracelets watches].freeze
  
  scope :for_clothing, -> { where(name: CLOTHING_CATEGORIES) }
  scope :for_shoes, -> { where(name: SHOES_CATEGORIES) }
  scope :for_accessories, -> { where(name: ACCESSORIES_CATEGORIES) }
  scope :for_jewelry, -> { where(name: JEWELRY_CATEGORIES) }
end
