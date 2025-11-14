require "test_helper"

class BatchInventoryCreationJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @analysis = create(:clothing_analysis, user: @user, image_blob_id: @image_blob.id)
  end

  test "job queues correctly" do
    result1 = create(:extraction_result, :completed, clothing_analysis: @analysis, extracted_image_blob_id: @image_blob.id)
    result2 = create(:extraction_result, :completed, clothing_analysis: @analysis, extracted_image_blob_id: @image_blob.id)

    assert_enqueued_with(job: BatchInventoryCreationJob, args: [ [ result1.id, result2.id ], @user.id ]) do
      BatchInventoryCreationJob.perform_later([ result1.id, result2.id ], @user.id)
    end
  end

  test "job creates inventory items from extraction results" do
    result1 = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Blue Shirt",
        "category" => "Tops",
        "brand_name" => "Nike",
        "description" => "A blue shirt"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    result2 = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_002",
        "item_name" => "Black Jeans",
        "category" => "Bottoms",
        "description" => "Black jeans"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 2 do
      BatchInventoryCreationJob.perform_now([ result1.id, result2.id ], @user.id)
    end

    item1 = InventoryItem.find_by(name: "Blue Shirt")
    assert_not_nil item1
    assert_equal @user, item1.user
    assert_equal "A blue shirt", item1.description
    assert item1.primary_image.attached?, "Primary image should be attached"
    assert_equal @image_blob.id, item1.primary_image.blob.id

    item2 = InventoryItem.find_by(name: "Black Jeans")
    assert_not_nil item2
    assert_equal @user, item2.user
  end

  test "job stores extraction_prompt when creating items" do
    extraction_prompt = "PROFESSIONAL STOCK PHOTO EXTRACTION - TEST ITEM"
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Test Shirt",
        "category" => "Tops",
        "description" => "A test shirt",
        "extraction_prompt" => extraction_prompt
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    BatchInventoryCreationJob.perform_now([ result.id ], @user.id)

    item = InventoryItem.find_by(name: "Test Shirt")
    assert_not_nil item
    assert_equal extraction_prompt, item.extraction_prompt
  end

  test "job creates categories when they don't exist" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => "New Category #{SecureRandom.hex(4)}"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "Category.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert item.category.present?
    assert_equal result.item_data_hash["category"], item.category.name
  end

  test "job creates brands when they don't exist" do
    brand_name = "New Brand #{SecureRandom.hex(4)}"
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "brand_name" => brand_name
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "Brand.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert item.brand.present?
    assert_equal brand_name, item.brand.name
  end

  test "job skips extraction results that are not successful" do
    successful = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001", "item_name" => "Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    failed = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_002", "item_name" => "Pants" },
      status: "failed"
    )

    pending = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_003", "item_name" => "Shoes" },
      status: "pending"
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ successful.id, failed.id, pending.id ], @user.id)
    end
  end

  test "job handles errors gracefully when creating items" do
    # Create a result that will cause an error during item creation
    # Force an error by stubbing Category.find_or_create_by! to raise
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => "Tops"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)
    Rails.logger.stubs(:info) # Stub info logging
    Rails.logger.stubs(:error) # Stub error logging

    # Stub Category.find_or_create_by! to raise an error
    # This will be called in find_or_create_category when processing the item
    # The job catches the error in the each loop and re-raises in test environment
    Category.stubs(:find_or_create_by!).raises(StandardError.new("Database error"))

    # In test environment, the error will be re-raised from the inner rescue block (line 41)
    # The outer rescue block (line 52) also catches and re-raises
    assert_raises(StandardError, "Database error") do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    # No items should be created due to error
    assert_equal 0, InventoryItem.count
  end

  test "job broadcasts completion" do
    result1 = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001", "item_name" => "Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    result2 = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_002", "item_name" => "Pants" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    broadcast_calls = []
    ActionCable.server.expects(:broadcast).with(
      "batch_creation_#{@user.id}",
      has_entries(
        type: "batch_creation_complete",
        created_count: 2,
        total_count: 2
      )
    ).at_least_once

    BatchInventoryCreationJob.perform_now([ result1.id, result2.id ], @user.id)
  end

  test "job handles RecordNotFound errors" do
    # Job uses .where which doesn't raise RecordNotFound
    # It will just return empty results and skip processing
    # Should still broadcast completion (with 0 items)
    ActionCable.server.expects(:broadcast).with(
      "batch_creation_#{@user.id}",
      has_entries(
        type: "batch_creation_complete",
        created_count: 0,
        total_count: 0
      )
    )

    assert_nothing_raised do
      BatchInventoryCreationJob.perform_now([ 99999 ], @user.id)
    end

    # Should not create any items
    assert_equal 0, InventoryItem.count
  end

  test "job only processes extraction results for the specified user" do
    other_user = create(:user)
    other_analysis = create(:clothing_analysis, user: other_user, image_blob_id: @image_blob.id)

    user_result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001", "item_name" => "User Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    other_result = ExtractionResult.create!(
      clothing_analysis: other_analysis,
      item_data: { "id" => "item_002", "item_name" => "Other Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    # Should only create item for user_result, not other_result
    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ user_result.id, other_result.id ], @user.id)
    end

    assert InventoryItem.exists?(name: "User Shirt", user: @user)
    assert_not InventoryItem.exists?(name: "Other Shirt", user: @user)
  end

  test "job handles missing category name gracefully" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => nil
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    # When category is missing, job assigns default "Uncategorized" category
    assert_not_nil item.category
    assert_equal "Uncategorized", item.category.name
  end

  test "job handles missing brand name gracefully" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "brand_name" => nil
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert_nil item.brand
  end

  test "job handles empty extraction results list" do
    # Should still broadcast completion even with empty results
    ActionCable.server.expects(:broadcast).with(
      "batch_creation_#{@user.id}",
      has_entries(
        type: "batch_creation_complete",
        created_count: 0,
        total_count: 0
      )
    )

    assert_no_difference "InventoryItem.count" do
      BatchInventoryCreationJob.perform_now([], @user.id)
    end
  end

  test "job handles StandardError during execution" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001", "item_name" => "Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    # Force an error in Category.find_or_create_by! (will be called via default_category)
    # Since category is nil, it will call default_category which calls find_or_create_by!
    Category.stubs(:find_or_create_by!).raises(StandardError.new("Database error"))

    ActionCable.server.stubs(:broadcast)
    Rails.logger.stubs(:info) # Stub info logging
    Rails.logger.stubs(:error) # Stub error logging

    # In test environment, the inner rescue re-raises (line 41), so the error should propagate
    # The outer rescue block (line 52) also catches and re-raises
    assert_raises(StandardError, "Database error") do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end
  end

  test "job uses existing category when category already exists" do
    existing_category = create(:category, name: "Existing Category")
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => existing_category.name
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_no_difference "Category.count" do
      assert_difference "InventoryItem.count", 1 do
        BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
      end
    end

    item = InventoryItem.last
    assert_equal existing_category, item.category
  end

  test "job uses existing brand when brand already exists" do
    existing_brand = create(:brand, name: "Existing Brand")
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "brand_name" => existing_brand.name
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_no_difference "Brand.count" do
      assert_difference "InventoryItem.count", 1 do
        BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
      end
    end

    item = InventoryItem.last
    assert_equal existing_brand, item.brand
  end

  test "job handles extraction result without extracted_image_blob_id" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt"
      },
      status: "completed",
      extracted_image_blob_id: nil
    )

    ActionCable.server.stubs(:broadcast)

    # Should still create item, but extraction_successful? will be false
    # So it should be skipped
    assert_no_difference "InventoryItem.count" do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end
  end

  test "job handles item_data with symbol keys" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        id: "item_001",
        item_name: "Shirt",
        category: "Tops"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert_equal "Shirt", item.name
  end

  test "job handles item_data with empty string category" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => ""
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    # When category is missing, job assigns default "Uncategorized" category
    assert_not_nil item.category
    assert_equal "Uncategorized", item.category.name
  end

  test "job handles item_data with empty string brand" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "brand_name" => ""
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert_nil item.brand
  end

  test "job sets clothing_analysis on created items" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    BatchInventoryCreationJob.perform_now([ result.id ], @user.id)

    item = InventoryItem.last
    assert_equal @analysis, item.clothing_analysis
  end

  test "job uses default name when item_name is missing" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    item = InventoryItem.last
    assert_equal "Extracted Item", item.name
  end

  test "job query correctly filters by user through clothing_analysis association" do
    other_user = create(:user)
    other_analysis = create(:clothing_analysis, user: other_user, image_blob_id: @image_blob.id)

    user_result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: { "id" => "item_001", "item_name" => "User Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    other_result = ExtractionResult.create!(
      clothing_analysis: other_analysis,
      item_data: { "id" => "item_002", "item_name" => "Other Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    # Pass both IDs, but should only process user_result
    assert_difference "InventoryItem.count", 1 do
      BatchInventoryCreationJob.perform_now([ user_result.id, other_result.id ], @user.id)
    end

    # Verify only user's item was created
    assert InventoryItem.exists?(name: "User Shirt", user: @user)
    assert_not InventoryItem.exists?(name: "Other Shirt", user: @user)
  end

  test "job handles case where no extraction results match user filter" do
    other_user = create(:user)
    other_analysis = create(:clothing_analysis, user: other_user, image_blob_id: @image_blob.id)

    other_result = ExtractionResult.create!(
      clothing_analysis: other_analysis,
      item_data: { "id" => "item_001", "item_name" => "Other Shirt" },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    # Should not create any items since other_result belongs to other_user
    assert_no_difference "InventoryItem.count" do
      BatchInventoryCreationJob.perform_now([ other_result.id ], @user.id)
    end
  end

  test "job logs error when item creation fails" do
    result = ExtractionResult.create!(
      clothing_analysis: @analysis,
      item_data: {
        "id" => "item_001",
        "item_name" => "Shirt",
        "category" => "Tops"
      },
      status: "completed",
      extracted_image_blob_id: @image_blob.id
    )

    ActionCable.server.stubs(:broadcast)

    # Force an error in InventoryItem.create!
    InventoryItem.stubs(:create!).raises(StandardError.new("Database error"))

    # Stub logging calls first
    Rails.logger.stubs(:info)
    Rails.logger.stubs(:warn)

    # Capture error logs
    error_logs = []
    Rails.logger.stubs(:error).with {  |msg| error_logs << msg; true }

    # In test environment, the error will be re-raised, so expect it
    assert_raises(StandardError) do
      BatchInventoryCreationJob.perform_now([ result.id ], @user.id)
    end

    # Verify error was logged
    assert error_logs.any? { |log| log.to_s.include?("Failed to create inventory item") },
      "Expected error log to include 'Failed to create inventory item', got: #{error_logs.inspect}"
  end
end
