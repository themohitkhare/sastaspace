class AddVectorToInventoryItems < ActiveRecord::Migration[8.1]
  def change
    # Check if column exists and is the wrong type
    if column_exists?(:inventory_items, :embedding_vector)
      # Drop the existing bytea column and recreate as vector
      remove_column :inventory_items, :embedding_vector
      add_column :inventory_items, :embedding_vector, :vector, limit: 1536
    else
      # Add new vector column
      add_column :inventory_items, :embedding_vector, :vector, limit: 1536
    end
    
    # Add HNSW index for vector similarity search
    add_index :inventory_items, :embedding_vector, using: :hnsw, opclass: :vector_cosine_ops
  end
end
