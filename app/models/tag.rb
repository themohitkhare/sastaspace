class Tag < ApplicationRecord
  validates :name, presence: true, uniqueness: true
  
  has_many :inventory_tags, dependent: :destroy
  has_many :inventory_items, through: :inventory_tags
  
  scope :popular, -> { joins(:inventory_tags).group('tags.id').order('COUNT(inventory_tags.id) DESC') }
end
