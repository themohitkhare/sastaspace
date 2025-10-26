class InventoryTag < ApplicationRecord
  belongs_to :inventory_item
  belongs_to :tag

  validates :inventory_item_id, uniqueness: { scope: :tag_id }
end
