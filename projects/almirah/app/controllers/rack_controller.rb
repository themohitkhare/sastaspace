# frozen_string_literal: true

class RackController < ApplicationController
  def index
    @ethnic_items  = Item.by_rack("ethnic")
    @office_items  = Item.by_rack("office")
    @weekend_items = Item.by_rack("weekend")
    @gap_suggestions = GapSuggestion.all.order(:id)

    @total_items = Item.count
  end
end
