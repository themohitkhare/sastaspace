class Outfit < ApplicationRecord
  belongs_to :user

  has_many :outfit_items, dependent: :destroy
  has_many :inventory_items, through: :outfit_items

  validates :name, presence: true

  scope :favorites, -> { where(is_favorite: true) }
end
