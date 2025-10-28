class Brand < ApplicationRecord
  validates :name, presence: true, uniqueness: true

  has_many :inventory_items, dependent: :restrict_with_exception

  scope :popular, -> { order(:name) }
end
