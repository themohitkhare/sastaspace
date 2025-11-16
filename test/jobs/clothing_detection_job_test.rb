require "test_helper"

class ClothingDetectionJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
  end

  test "job queues correctly" do
    assert_enqueued_with(job: ClothingDetectionJob, args: [ @image_blob.id, @user.id ]) do
      ClothingDetectionJob.perform_later(@image_blob.id, @user.id)
    end
  end

  test "job performs detection and creates analysis" do
    category1 = create(:category, name: "Tops")
    category2 = create(:category, name: "Bottoms")
    # Stub the detection service
    mock_result = {
      "total_items_detected" => 2,
      "people_count" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Blue Shirt",
          "category_id" => category1.id,
          "gender_styling" => "men",
          "confidence" => 0.9,
          "description" => "A blue shirt"
        },
        {
          "id" => "item_002",
          "item_name" => "Black Jeans",
          "category_id" => category2.id,
          "gender_styling" => "unisex",
          "confidence" => 0.85,
          "description" => "Black jeans"
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    # Stub blob attachment service
    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    # Stub ActionCable broadcasts
    ActionCable.server.stubs(:broadcast)

    assert_difference "ClothingAnalysis.count", 1 do
      assert_difference "InventoryItem.count", 2 do
        ClothingDetectionJob.perform_now(@image_blob.id, @user.id)
      end
    end

    analysis = ClothingAnalysis.last
    assert_equal @user, analysis.user
    assert_equal @image_blob.id, analysis.image_blob_id
    assert_equal 2, analysis.items_detected
    assert_equal "completed", analysis.status
  end

  test "job handles detection errors" do
    mock_result = {
      "error" => "Detection failed",
      "items" => [],
      "total_items_detected" => 0
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    ActionCable.server.stubs(:broadcast)

    assert_difference "ClothingAnalysis.count", 1 do
      assert_no_difference "InventoryItem.count" do
        ClothingDetectionJob.perform_now(@image_blob.id, @user.id)
      end
    end

    analysis = ClothingAnalysis.last
    assert_equal "failed", analysis.status
    assert_equal 0, analysis.items_detected
  end

  test "job broadcasts progress updates" do
    category = create(:category, name: "Tops")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Shirt",
          "category_id" => category.id,
          "gender_styling" => "men",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    Services::BlobAttachmentService.stubs(:new).returns(stub(attach_primary_image_from_blob_id: true))

    ActionCable.server.expects(:broadcast).with(
      "detection_#{@user.id}",
      has_entries(type: "progress_update")
    ).at_least_once
    ActionCable.server.expects(:broadcast).with(
      "detection_#{@user.id}",
      has_entries(type: "detection_complete", items_detected: 1)
    ).at_least_once

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)
  end

  test "job broadcasts error on detection failure" do
    mock_result = {
      "error" => "Service unavailable",
      "items" => [],
      "total_items_detected" => 0
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    # Allow progress broadcasts
    ActionCable.server.stubs(:broadcast).with(
      "detection_#{@user.id}",
      has_entries(type: "progress_update")
    )
    ActionCable.server.expects(:broadcast).with(
      "detection_#{@user.id}",
      has_entries(type: "detection_error")
    ).at_least_once

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)
  end

  test "job handles RecordNotFound errors" do
    # Job will raise RecordNotFound when blob not found
    ActionCable.server.stubs(:broadcast)

    assert_raises(ActiveRecord::RecordNotFound) do
      ClothingDetectionJob.perform_now(99999, @user.id)
    end
  end

  test "job calculates average confidence" do
    mock_result = {
      "total_items_detected" => 3,
      "items" => [
        { "id" => "item_001", "confidence" => 0.9 },
        { "id" => "item_002", "confidence" => 0.8 },
        { "id" => "item_003", "confidence" => 0.7 }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    Services::BlobAttachmentService.stubs(:new).returns(stub(attach_primary_image_from_blob_id: true))
    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    analysis = ClothingAnalysis.last
    # Average of 0.9, 0.8, 0.7 = 0.8
    assert_equal 0.8, analysis.confidence
  end

  test "job handles items without confidence" do
    mock_result = {
      "total_items_detected" => 2,
      "items" => [
        { "id" => "item_001", "confidence" => 0.9 },
        { "id" => "item_002" } # No confidence
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    Services::BlobAttachmentService.stubs(:new).returns(stub(attach_primary_image_from_blob_id: true))
    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    analysis = ClothingAnalysis.last
    # Average of 0.9 and 0.0 (default) = 0.45
    assert_equal 0.45, analysis.confidence
  end

  test "job uses LLM description when available" do
    category = create(:category, name: "Tops")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Shirt",
          "category_id" => category.id,
          "gender_styling" => "men",
          "confidence" => 0.9,
          "description" => "LLM-generated description"
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    assert_equal "LLM-generated description", item.description
  end

  test "job builds description when LLM description not available" do
    category = create(:category, name: "Tops")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Blue Shirt",
          "category_id" => category.id,
          "subcategory" => "t-shirt",
          "color_primary" => "blue",
          "material_type" => "cotton",
          "gender_styling" => "men",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    assert item.description.present?, "Description should be present. Got: #{item.description.inspect}"
    assert item.description.include?("Blue Shirt"), "Description should include 'Blue Shirt'. Got: #{item.description.inspect}"
  end

  test "job builds description with all optional fields" do
    category = create(:category, name: "Dresses")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Red Dress",
          "category_id" => category.id,
          "subcategory" => "maxi",
          "color_primary" => "red",
          "color_secondary" => "pink",
          "material_type" => "silk",
          "pattern_type" => "floral",
          "pattern_details" => "rose pattern",
          "style_category" => "formal",
          "gender_styling" => "women",
          "confidence" => 0.95
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    description = item.description
    assert description.present?, "Description should be present. Got: #{description.inspect}"
    assert description.include?("Red Dress"), "Description should include 'Red Dress'. Got: #{description.inspect}"
    assert description.include?("red and pink"), "Description should include 'red and pink'. Got: #{description.inspect}"
    assert description.include?("silk"), "Description should include 'silk'. Got: #{description.inspect}"
    assert description.include?("rose pattern"), "Description should include 'rose pattern'. Got: #{description.inspect}"
    assert description.include?("formal"), "Description should include 'formal'. Got: #{description.inspect}"
    assert description.include?("women"), "Description should include 'women'. Got: #{description.inspect}"
  end

  test "job builds description with solid pattern (should not include pattern)" do
    category = create(:category, name: "Bottoms")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Blue Jeans",
          "category_id" => category.id,
          "color_primary" => "blue",
          "pattern_type" => "solid",
          "gender_styling" => "unisex",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    description = item.description
    assert_not description.include?("pattern"), "Solid pattern should not be mentioned"
    assert description.include?("unisex")
  end

  test "job builds description with minimal data" do
    category = create(:category, name: "Uncategorized")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Item",
          "category_id" => category.id
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    assert item.description.present?
    assert item.description.include?("Item")
  end

  test "job handles category normalization with subcategory" do
    parent_category = create(:category, name: "Tops")
    subcategory = create(:category, name: "T-Shirts", parent_id: parent_category.id)

    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Shirt",
          "category_id" => subcategory.id,
          "gender_styling" => "men",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_equal parent_category.id, item.category_id
    assert_equal subcategory.id, item.subcategory_id
  end

  test "job handles errors when creating inventory items" do
    category = create(:category, name: "Tops")
    initial_count = @user.inventory_items.count
    mock_result = {
      "total_items_detected" => 2,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Valid Item",
          "category_id" => category.id,
          "gender_styling" => "men",
          "confidence" => 0.9
        },
        {
          "id" => "item_002",
          "item_name" => nil, # Invalid - will cause validation error
          "category_id" => category.id,
          "gender_styling" => "women",
          "confidence" => 0.85
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)
    Rails.logger.stubs(:error)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    # Should create only the valid item (name nil will use default "Extracted Item")
    assert_equal initial_count + 2, @user.inventory_items.count
  end

  test "job handles attachment service errors gracefully" do
    category = create(:category, name: "Tops")
    initial_count = @user.inventory_items.count
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "Shirt",
          "category_id" => category.id,
          "gender_styling" => "men",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).raises(StandardError.new("Attachment failed"))
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    # Should not raise, just log error
    assert_nothing_raised do
      ClothingDetectionJob.perform_now(@image_blob.id, @user.id)
    end

    # Item should still be created
    assert_equal initial_count + 1, @user.inventory_items.count
  end

  test "job builds description when item_name includes subcategory" do
    category = create(:category, name: "Tops")
    mock_result = {
      "total_items_detected" => 1,
      "items" => [
        {
          "id" => "item_001",
          "item_name" => "T-Shirt", # Already includes "t-shirt"
          "category_id" => category.id,
          "subcategory" => "t-shirt",
          "gender_styling" => "men",
          "confidence" => 0.9
        }
      ]
    }

    mock_service = stub
    mock_service.stubs(:analyze).returns(mock_result)
    ClothingDetectionService.stubs(:new).returns(mock_service)

    mock_attachment_service = stub
    mock_attachment_service.stubs(:attach_primary_image_from_blob_id).returns(true)
    Services::BlobAttachmentService.stubs(:new).returns(mock_attachment_service)

    ActionCable.server.stubs(:broadcast)

    ClothingDetectionJob.perform_now(@image_blob.id, @user.id)

    item = InventoryItem.last
    assert_not_nil item, "Inventory item should be created"
    # Should not duplicate subcategory in description
    assert_not item.description.include?("(t-shirt)"), "Should not duplicate subcategory if already in name"
  end
end
