# frozen_string_literal: true

class Outfit < ApplicationRecord
  self.table_name = "project_almirah.outfits"
  self.primary_key = "id"

  belongs_to :user

  has_many :outfit_items, foreign_key: "outfit_id", dependent: :destroy
  has_many :items, through: :outfit_items

  validates :name, presence: true
end
