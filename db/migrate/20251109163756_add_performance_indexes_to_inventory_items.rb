class AddPerformanceIndexesToInventoryItems < ActiveRecord::Migration[8.1]
  def up
    # Composite index for common query pattern: user_id + category_id + status
    # Used in filtered list views and category pages
    unless index_exists?(:inventory_items, [ :user_id, :category_id, :status ])
      add_index :inventory_items, [ :user_id, :category_id, :status ],
                name: "index_inventory_items_on_user_category_status"
    end

    # Composite index for user_id + status (for filtering by status)
    # Used when filtering active/archived/sold items
    unless index_exists?(:inventory_items, [ :user_id, :status ])
      add_index :inventory_items, [ :user_id, :status ],
                name: "index_inventory_items_on_user_status"
    end

    # JSON metadata indexes for common filter patterns
    # Using expression indexes on JSONB fields for efficient filtering
    # Index for season filtering (metadata->>'season')
    execute <<-SQL
      CREATE INDEX IF NOT EXISTS index_inventory_items_on_metadata_season
      ON inventory_items ((metadata->>'season'))
      WHERE metadata->>'season' IS NOT NULL
    SQL

    # Index for color filtering (metadata->>'color')
    # Using expression index for efficient LIKE queries
    execute <<-SQL
      CREATE INDEX IF NOT EXISTS index_inventory_items_on_metadata_color
      ON inventory_items ((metadata->>'color'))
      WHERE metadata->>'color' IS NOT NULL
    SQL

    # Composite index for user_id + metadata season (common filter combination)
    execute <<-SQL
      CREATE INDEX IF NOT EXISTS index_inventory_items_on_user_metadata_season
      ON inventory_items (user_id, (metadata->>'season'))
      WHERE metadata->>'season' IS NOT NULL
    SQL

    # Composite index for user_id + metadata color (common filter combination)
    execute <<-SQL
      CREATE INDEX IF NOT EXISTS index_inventory_items_on_user_metadata_color
      ON inventory_items (user_id, (metadata->>'color'))
      WHERE metadata->>'color' IS NOT NULL
    SQL

    # Index for last_worn_at queries (used in recently_worn scope)
    # Already exists, but ensure it's optimized
    unless index_exists?(:inventory_items, :last_worn_at)
      add_index :inventory_items, :last_worn_at
    end

    # Composite index for user_id + last_worn_at (for user-specific recently_worn queries)
    unless index_exists?(:inventory_items, [ :user_id, :last_worn_at ])
      add_index :inventory_items, [ :user_id, :last_worn_at ],
                name: "index_inventory_items_on_user_last_worn_at"
    end

    # Index for wear_count (used in most_worn scope)
    unless index_exists?(:inventory_items, :wear_count)
      add_index :inventory_items, :wear_count
    end

    # Composite index for user_id + wear_count (for user-specific most_worn queries)
    unless index_exists?(:inventory_items, [ :user_id, :wear_count ])
      add_index :inventory_items, [ :user_id, :wear_count ],
                name: "index_inventory_items_on_user_wear_count"
    end
  end

  def down
    # Remove all indexes added in this migration
    remove_index :inventory_items, name: "index_inventory_items_on_user_category_status" if index_exists?(:inventory_items, [ :user_id, :category_id, :status ], name: "index_inventory_items_on_user_category_status")
    remove_index :inventory_items, name: "index_inventory_items_on_user_status" if index_exists?(:inventory_items, [ :user_id, :status ], name: "index_inventory_items_on_user_status")
    remove_index :inventory_items, name: "index_inventory_items_on_user_last_worn_at" if index_exists?(:inventory_items, [ :user_id, :last_worn_at ], name: "index_inventory_items_on_user_last_worn_at")
    remove_index :inventory_items, name: "index_inventory_items_on_user_wear_count" if index_exists?(:inventory_items, [ :user_id, :wear_count ], name: "index_inventory_items_on_user_wear_count")

    execute "DROP INDEX IF EXISTS index_inventory_items_on_metadata_season"
    execute "DROP INDEX IF EXISTS index_inventory_items_on_metadata_color"
    execute "DROP INDEX IF EXISTS index_inventory_items_on_user_metadata_season"
    execute "DROP INDEX IF EXISTS index_inventory_items_on_user_metadata_color"
  end
end
