# frozen_string_literal: true

class PlanController < ApplicationController
  def show
    # Occasion planner page — placeholder for v2 AI ranking.
    @outfits = Outfit.includes(:items).order(created_at: :desc).limit(10)
  end
end
