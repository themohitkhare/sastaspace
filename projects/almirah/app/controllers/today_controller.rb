# frozen_string_literal: true

class TodayController < ApplicationController
  def show
    # Pick items not worn in the longest time for a "due for a wear" suggestion.
    @picks = Item.order(Arel.sql("last_worn_at ASC NULLS FIRST")).limit(3)
  end
end
