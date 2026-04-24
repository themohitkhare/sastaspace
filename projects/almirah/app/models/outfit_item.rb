# frozen_string_literal: true

class OutfitItem < ApplicationRecord
  self.table_name = "project_almirah.outfit_items"
  self.primary_key = nil # composite PK (outfit_id, item_id)

  belongs_to :outfit, foreign_key: "outfit_id"
  belongs_to :item,   foreign_key: "item_id"
end
