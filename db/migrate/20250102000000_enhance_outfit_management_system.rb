class EnhanceOutfitManagementSystem < ActiveRecord::Migration[8.1]
  def change
    # Add metadata JSON field to outfits
    add_column :outfits, :metadata, :jsonb, default: {}

    # Add status enum to outfits (will use integer)
    add_column :outfits, :status, :integer, default: 0

    # Add wear tracking to outfits
    add_column :outfits, :worn_count, :integer, default: 0
    add_column :outfits, :last_worn_at, :datetime

    # Add wear tracking and styling notes to outfit_items
    add_column :outfit_items, :worn_count, :integer, default: 0
    add_column :outfit_items, :last_worn_at, :datetime
    add_column :outfit_items, :styling_notes, :text

    # Add indexes for better query performance
    add_index :outfits, [ :user_id, :status ]
    # Add unique index if it doesn't already exist (may have been added in a previous migration)
    unless index_exists?(:outfit_items, [ :outfit_id, :inventory_item_id ], unique: true)
      add_index :outfit_items, [ :outfit_id, :inventory_item_id ], unique: true, name: "index_outfit_items_unique"
    end

    # Add index on metadata for occasion and season queries
    add_index :outfits, "(metadata->>'occasion')", name: "index_outfits_on_occasion_metadata"
    add_index :outfits, "(metadata->>'season')", name: "index_outfits_on_season_metadata"
  end
end
