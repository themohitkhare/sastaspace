# frozen_string_literal: true

class ProfilesController < ApplicationController
  def show
    @user = current_user
    @total_items   = Item.count
    @ethnic_count  = Item.by_rack("ethnic").count
    @office_count  = Item.by_rack("office").count
    @weekend_count = Item.by_rack("weekend").count
    @wears_total   = WearEvent.joins(:item).count
  end
end
