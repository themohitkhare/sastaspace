class EnhanceOutfitManagementSystem < ActiveRecord::Migration[8.1]
  def change
    # NOTE: This migration is now mostly consolidated into create_outfits and create_outfit_items
    # Keeping this migration for backwards compatibility, but most fields are now in the create migrations
    # Only adding fields that might not exist if migrations are run out of order

    # These fields are now in create_outfits, but adding conditionally for safety
    unless column_exists?(:outfits, :metadata)
      add_column :outfits, :metadata, :jsonb, default: {}
    end
    unless column_exists?(:outfits, :status)
      add_column :outfits, :status, :integer, default: 0
    end
    unless column_exists?(:outfits, :worn_count)
      add_column :outfits, :worn_count, :integer, default: 0
    end
    unless column_exists?(:outfits, :last_worn_at)
      add_column :outfits, :last_worn_at, :datetime
    end

    # These fields are now in create_outfit_items, but adding conditionally for safety
    unless column_exists?(:outfit_items, :worn_count)
      add_column :outfit_items, :worn_count, :integer, default: 0
    end
    unless column_exists?(:outfit_items, :last_worn_at)
      add_column :outfit_items, :last_worn_at, :datetime
    end
    unless column_exists?(:outfit_items, :styling_notes)
      add_column :outfit_items, :styling_notes, :text
    end

    # Add indexes for better query performance (now in create migrations, but adding conditionally)
    add_index :outfits, [ :user_id, :status ] unless index_exists?(:outfits, [ :user_id, :status ])
    unless index_exists?(:outfit_items, [ :outfit_id, :inventory_item_id ], unique: true)
      add_index :outfit_items, [ :outfit_id, :inventory_item_id ], unique: true, name: "index_outfit_items_unique"
    end
    unless index_exists?(:outfits, "(metadata->>'occasion')")
      add_index :outfits, "(metadata->>'occasion')", name: "index_outfits_on_occasion_metadata"
    end
    unless index_exists?(:outfits, "(metadata->>'season')")
      add_index :outfits, "(metadata->>'season')", name: "index_outfits_on_season_metadata"
    end
  end
end
