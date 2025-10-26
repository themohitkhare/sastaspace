class AddCreatedAtIndexesToTables < ActiveRecord::Migration[8.1]
  def change
    # Add index on created_at for inventory_items to support sorting
    add_index :inventory_items, :created_at unless index_exists?(:inventory_items, :created_at)

    # Add index on created_at for categories to support sorting
    add_index :categories, :created_at unless index_exists?(:categories, :created_at)

    # Add index on created_at for users to support sorting
    add_index :users, :created_at unless index_exists?(:users, :created_at)

    # Add index on user_id and created_at for inventory_items for efficient user queries
    unless index_exists?(:inventory_items, [ :user_id, :created_at ], name: 'index_inventory_items_on_user_id_and_created_at')
      add_index :inventory_items, [ :user_id, :created_at ],
                name: 'index_inventory_items_on_user_id_and_created_at'
    end
  end
end
