# frozen_string_literal: true

class DiscoverController < ApplicationController
  def show
    @gap_suggestions = GapSuggestion.all.order(:id)
    # Trend items — items not worn in >90 days that could be revived.
    @unworn = Item.where("last_worn_at < ? OR last_worn_at IS NULL", 90.days.ago)
                  .order(Arel.sql("last_worn_at ASC NULLS FIRST"))
                  .limit(6)
  end
end
