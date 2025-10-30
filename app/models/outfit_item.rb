class OutfitItem < ApplicationRecord
  belongs_to :outfit
  belongs_to :inventory_item

  validates :position, numericality: { greater_than_or_equal_to: 0 }, allow_nil: true
end
