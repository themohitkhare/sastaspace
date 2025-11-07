class OutfitItem < ApplicationRecord
  belongs_to :outfit
  belongs_to :inventory_item

  validates :outfit_id, uniqueness: { scope: :inventory_item_id }
  validates :position, numericality: { greater_than_or_equal_to: 0 }, allow_nil: true
  validates :worn_count, numericality: { greater_than_or_equal_to: 0 }, allow_nil: true

  scope :worn_recently, -> { where("last_worn_at > ?", 30.days.ago) }

  after_initialize :set_defaults, if: :new_record?

  private

  def set_defaults
    self.worn_count ||= 0
  end
end
