# frozen_string_literal: true

class ItemsController < ApplicationController
  def show
    @item = Item.find(params[:id])
    @wear_events = @item.wear_events.recent.limit(10)
    @pairings = compute_pairings(@item)
  rescue ActiveRecord::RecordNotFound
    redirect_to root_path, alert: "Item not found."
  end

  private

  def compute_pairings(item)
    # Seed the two hardcoded pairings for i05, else default to rack-mates.
    hardcoded = {
      "i05" => [
        { title: "formal — wedding",   item_ids: %w[i09 i15 i12] },
        { title: "understated — puja", item_ids: %w[i10 i14 i11] },
      ],
    }

    decks = hardcoded.fetch(item.id) do
      rack_mates = Item.by_rack(item.rack).where.not(id: item.id).limit(6)
      first  = rack_mates.first(3)
      second = rack_mates.drop(3)
      decks_from_items = [ { title: "a natural pairing", items: first } ]
      decks_from_items << { title: "an alternate", items: second } if second.size >= 2
      return decks_from_items
    end

    decks.map do |d|
      ids = d[:item_ids]
      items = ids.filter_map { |id| Item.find_by(id: id) }
      { title: d[:title], items: items }
    end
  end
end
