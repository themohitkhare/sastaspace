# frozen_string_literal: true

class SearchController < ApplicationController
  def index
    @query = params[:q].to_s.strip
    @results = if @query.present?
      # Simple full-text search across name, kind, tone, rack.
      Item.where(
        "name ILIKE :q OR kind ILIKE :q OR tone ILIKE :q OR rack ILIKE :q",
        q: "%#{Item.sanitize_sql_like(@query)}%"
      ).order(:rack, :id).limit(50)
    else
      Item.none
    end
  end
end
