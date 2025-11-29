class UpdateEmbeddingVectorDimensionsTo1024 < ActiveRecord::Migration[8.1]
  def up
    # Remove the HNSW index first (required before changing column)
    if index_exists?(:inventory_items, :embedding_vector)
      remove_index :inventory_items, :embedding_vector
    end

    # Change the vector column limit from 1536 to 1024
    # This matches mxbai-embed-large:latest which returns 1024 dimensions
    change_column :inventory_items, :embedding_vector, :vector, limit: 1024

    # Recreate the HNSW index for vector similarity search
    add_index :inventory_items, :embedding_vector, using: :hnsw, opclass: :vector_cosine_ops
  end

  def down
    # Remove the HNSW index
    if index_exists?(:inventory_items, :embedding_vector)
      remove_index :inventory_items, :embedding_vector
    end

    # Revert to 1536 dimensions
    change_column :inventory_items, :embedding_vector, :vector, limit: 1536

    # Recreate the HNSW index
    add_index :inventory_items, :embedding_vector, using: :hnsw, opclass: :vector_cosine_ops
  end
end
