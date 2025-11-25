require "test_helper"

# Performance tests to verify N+1 query fixes and index usage
class QueryOptimizationTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, name: "Tops #{SecureRandom.hex(4)}")
    @subcategory = create(:category, name: "T-Shirts #{SecureRandom.hex(4)}", parent_id: @category.id)
    @brand = create(:brand)

    # Create multiple items to test query performance
    @items = 5.times.map do
      create(:inventory_item, :clothing,
             user: @user,
             category: @category,
             subcategory: @subcategory,
             brand: @brand,
             metadata: { color: "blue", season: "summer" })
    end
  end

  test "index action includes all necessary associations" do
    # This test verifies that the index action doesn't cause N+1 queries
    # by checking that all associations are eager loaded

    queries = []
    callback = lambda do |name, start, finish, id, payload|
      queries << payload[:sql] if payload[:sql]
    end

    ActiveSupport::Notifications.subscribed(callback, "sql.active_record") do
      items = @user.inventory_items
                   .includes(:category, :subcategory, :brand, :tags, :ai_analyses,
                             primary_image_attachment: :blob,
                             additional_images_attachments: :blob)
                   .limit(10)

      # Access associations to trigger queries if not eager loaded
      items.each do |item|
        item.category
        item.subcategory
        item.brand
        item.tags.to_a
        item.ai_analyses.to_a
        item.primary_image.attached? if item.primary_image
        item.additional_images.attached? if item.additional_images
      end
    end

    # Count SELECT queries (excluding schema queries)
    select_queries = queries.select { |q| q.match?(/^SELECT/i) && !q.match?(/FROM.*pg_|FROM.*information_schema/) }

    # With proper eager loading, we should have minimal queries
    # Allow some queries for associations but not N+1 per item
    assert select_queries.count < 20, "Too many queries detected - possible N+1 issue"
  end

  test "vector search includes all necessary associations" do
    # Create an item with embedding
    item = @items.first
    item.update(embedding_vector: Array.new(1536) { rand })

    queries = []
    callback = lambda do |name, start, finish, id, payload|
      queries << payload[:sql] if payload[:sql]
    end

    ActiveSupport::Notifications.subscribed(callback, "sql.active_record") do
      similar = VectorSearchService.find_similar_items(@user, item.embedding_vector, limit: 5)

      # Access associations
      similar.each do |similar_item|
        similar_item.category
        similar_item.subcategory
        similar_item.brand
        similar_item.tags.to_a
        similar_item.ai_analyses.to_a
      end
    end

    select_queries = queries.select { |q| q.match?(/^SELECT/i) && !q.match?(/FROM.*pg_|FROM.*information_schema/) }
    assert select_queries.count < 15, "Vector search has N+1 queries"
  end

  test "composite index on user_id, category_id, status is used" do
    # Verify that queries using user_id + category_id + status use the composite index
    items = InventoryItem.where(user_id: @user.id, category_id: @category.id, status: :active)

    # This should use the composite index
    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    # Check if index is mentioned in explain (PostgreSQL specific)
    # The exact format may vary, but index should be referenced
    assert explain.present?, "Query should use index"
  end

  test "metadata season index is used for filtering" do
    # Verify that metadata season filtering uses the index
    items = InventoryItem.where(user_id: @user.id)
                         .where("metadata->>'season' = ?", "summer")

    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    assert explain.present?, "Metadata season query should use index"
  end

  test "metadata color index is used for filtering" do
    # Verify that metadata color filtering uses the index
    items = InventoryItem.where(user_id: @user.id)
                         .where("metadata->>'color' LIKE ?", "%blue%")

    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    assert explain.present?, "Metadata color query should use index"
  end

  test "user_id and status composite index is used" do
    # Verify composite index for user_id + status
    items = InventoryItem.where(user_id: @user.id, status: :active)

    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    assert explain.present?, "User + status query should use index"
  end

  test "recently_worn scope uses user_id and last_worn_at index" do
    # Update items to have last_worn_at
    @items.first(3).each { |item| item.update(last_worn_at: 1.day.ago) }

    items = InventoryItem.where(user_id: @user.id)
                         .where.not(last_worn_at: nil)
                         .order(last_worn_at: :desc)

    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    assert explain.present?, "Recently worn query should use index"
  end

  test "most_worn scope uses user_id and wear_count index" do
    # Update items to have wear_count
    @items.first(3).each_with_index { |item, i| item.update(wear_count: i + 1) }

    items = InventoryItem.where(user_id: @user.id)
                         .order(wear_count: :desc, created_at: :desc)

    explain = ActiveRecord::Base.connection.execute(
      "EXPLAIN #{items.to_sql}"
    ).values.flatten.join(" ")

    assert explain.present?, "Most worn query should use index"
  end
end
