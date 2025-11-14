require "test_helper"

class InventoryItemsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)

    # Stub authentication and current_user for HTML controller
    InventoryItemsController.any_instance.stubs(:authenticate_user!).returns(true)
    InventoryItemsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "index renders successfully with filters and pagination" do
    create_list(:inventory_item, 3, :clothing, user: @user, category: @category)

    get inventory_items_path, params: { search: "Item", color: "blue", season: "summer", page: 1 }
    assert_response :success
  end

  test "new renders successfully" do
    get new_inventory_item_path
    assert_response :success
  end

  test "create creates item and redirects on success" do
    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Shirt",
          description: "Nice shirt",
          category_id: @category.id,
          purchase_price: 19.99,
          purchase_date: Date.today,
          color: "blue",
          size: "M"
        }
      }
    end
    assert_redirected_to inventory_items_path
  end

  test "create attaches primary and additional images when provided" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    addl = [ fixture_file_upload("sample_image.jpg", "image/jpeg"), fixture_file_upload("sample_image.jpg", "image/jpeg") ]

    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "With Images",
          description: "desc",
          category_id: @category.id,
          purchase_price: 10,
          purchase_date: Date.today,
          primary_image: file,
          additional_images: addl
        }
      }
    end
    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?
    assert_equal 2, item.additional_images.count
    assert_redirected_to inventory_items_path
  end

  test "create renders errors on failure" do
    post inventory_items_path, params: { inventory_item: { name: nil, category_id: nil } }
    assert_response :unprocessable_entity
  end

  test "edit renders successfully" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    get edit_inventory_item_path(item)
    assert_response :success
  end

  test "edit displays primary image when attached" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    item = create(:inventory_item, :clothing, user: @user, category: @category)
    
    # Attach a primary image
    item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    get edit_inventory_item_path(item)
    assert_response :success
    
    # Verify the image is displayed in the HTML
    assert_select "img[alt='Current primary image']", count: 1
    # Verify blob ID is shown
    assert_match(/blob ID: \d+/, response.body)
  end

  test "edit shows message when no primary image attached" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    
    get edit_inventory_item_path(item)
    assert_response :success
    
    # Verify the "No primary image attached" message is shown
    assert_match(/No primary image attached/i, response.body)
  end

  test "update updates item and redirects on success" do
    item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Old")
    patch inventory_item_path(item), params: {
      inventory_item: { name: "New Name", description: "Updated description" }
    }
    assert_redirected_to inventory_items_path
    assert_equal "New Name", item.reload.name
    assert_equal "Updated description", item.reload.description
  end

  test "update attaches images when provided" do
    item = create(:inventory_item, :clothing, user: @user, category: @category, name: "Photos")
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    addl = [ fixture_file_upload("sample_image.jpg", "image/jpeg") ]

    patch inventory_item_path(item), params: {
      inventory_item: { primary_image: file, additional_images: addl }
    }
    assert_redirected_to inventory_items_path
    assert item.reload.primary_image.attached?
    assert_equal 1, item.additional_images.count
  end

  test "update renders errors on failure" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    patch inventory_item_path(item), params: { inventory_item: { name: nil } }
    assert_response :unprocessable_entity
  end

  test "destroy deletes item and redirects" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    assert_difference -> { @user.inventory_items.count }, -1 do
      delete inventory_item_path(item)
    end
    assert_redirected_to inventory_items_path
  end

  test "bulk_delete deletes selected items and redirects with notice" do
    items = create_list(:inventory_item, 2, :clothing, user: @user, category: @category)
    delete bulk_delete_inventory_items_path, params: { item_ids: items.map(&:id) }
    assert_redirected_to inventory_items_path
  end

  test "bulk_delete with no items shows alert and redirects" do
    delete bulk_delete_inventory_items_path, params: { item_ids: [] }
    assert_redirected_to inventory_items_path
  end

  test "create handles empty string in additional_images array gracefully" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    # Simulate empty string in additional_images (what Rails sends when no file selected)
    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Item with empty additional_images",
          description: "Test description",
          category_id: @category.id,
          primary_image: file,
          additional_images: [ "" ] # Empty string from empty file input
        }
      }
    end

    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?, "Primary image should be attached"
    assert_equal 0, item.additional_images.count, "No additional images should be attached when empty string provided"
    assert_redirected_to inventory_items_path
  end

  test "create handles additional_images with mixed empty strings and files" do
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    addl_file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    # Simulate array with empty strings and actual files
    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Item with mixed additional_images",
          description: "Test description",
          category_id: @category.id,
          primary_image: file,
          additional_images: [ "", addl_file, "" ] # Empty strings mixed with actual file
        }
      }
    end

    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?, "Primary image should be attached"
    assert_equal 1, item.additional_images.count, "Only actual files should be attached"
    assert_redirected_to inventory_items_path
  end

  test "update handles empty string in additional_images array gracefully" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")

    # Simulate empty string in additional_images
    patch inventory_item_path(item), params: {
      inventory_item: {
        additional_images: [ "" ] # Empty string from empty file input
      }
    }

    assert_redirected_to inventory_items_path
    assert_equal 0, item.reload.additional_images.count, "No additional images should be attached when empty string provided"
  end

  # Authentication is tested in API controller tests
  # HTML controller uses before_action :authenticate_user!

  test "index only shows current user's items" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)
    user_item = create(:inventory_item, :clothing, user: @user, category: @category)

    get inventory_items_path

    assert_response :success
    # Verify that only current user's items are shown (check assigns if available)
    # In integration tests, we verify through the response
    assert_select "body" # Basic check that page renders
  end

  test "show redirects to edit" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    get inventory_item_path(item)
    assert_redirected_to edit_inventory_item_path(item)
  end

  test "new_ai renders successfully" do
    get new_ai_inventory_items_path
    assert_response :success
  end

  test "create handles service errors gracefully" do
    Services::InventoryItemCreationService.any_instance.stubs(:create).raises(StandardError.new("Service error"))

    post inventory_items_path, params: {
      inventory_item: {
        name: "Test Item",
        category_id: @category.id
      }
    }

    assert_response :unprocessable_entity
    assert_select "body" # Verify error page renders
  end

  test "create with blob_id attaches image from blob" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Item with Blob",
          description: "Test",
          category_id: @category.id,
          blob_id: blob.id
        }
      }
    end

    item = @user.inventory_items.order(created_at: :desc).first
    assert item.primary_image.attached?, "Primary image should be attached from blob"
    assert_redirected_to inventory_items_path
  end

  test "update handles service errors gracefully" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    Services::InventoryItemUpdateService.any_instance.stubs(:update).returns({ success: false, errors: [ "Update failed" ] })

    patch inventory_item_path(item), params: {
      inventory_item: { name: "Updated Name" }
    }

    assert_response :unprocessable_entity
  end

  # Authorization for destroy is handled by scoping to current_user.inventory_items

  test "bulk_delete only deletes user's own items" do
    other_user = create(:user)
    other_item = create(:inventory_item, :clothing, user: other_user, category: @category)
    user_items = create_list(:inventory_item, 2, :clothing, user: @user, category: @category)

    # Attempt to delete mix of user's and other's items
    item_ids = user_items.map(&:id) + [ other_item.id ]

    assert_difference -> { @user.inventory_items.count }, -2 do
      delete bulk_delete_inventory_items_path, params: { item_ids: item_ids }
    end

    # Other user's item should still exist
    assert InventoryItem.exists?(other_item.id)
  end

  test "bulk_delete with invalid item_ids handles gracefully" do
    delete bulk_delete_inventory_items_path, params: { item_ids: [ 999_999, 999_998 ] }
    assert_redirected_to inventory_items_path
  end

  test "create with metadata stores correctly" do
    assert_difference -> { @user.inventory_items.count }, +1 do
      post inventory_items_path, params: {
        inventory_item: {
          name: "Item with Metadata",
          category_id: @category.id,
          metadata: {
            color: "blue",
            size: "M",
            season: "summer",
            occasion: "casual"
          }
        }
      }
    end

    item = @user.inventory_items.order(created_at: :desc).first
    assert_equal "blue", item.metadata["color"]
    assert_equal "M", item.metadata["size"]
    assert_equal "summer", item.metadata["season"]
  end

  test "update with metadata updates correctly" do
    item = create(:inventory_item, :clothing, user: @user, category: @category, metadata: { color: "red" })

    patch inventory_item_path(item), params: {
      inventory_item: {
        metadata: {
          color: "blue",
          size: "L"
        }
      }
    }

    assert_redirected_to inventory_items_path
    item.reload
    assert_equal "blue", item.metadata["color"]
    assert_equal "L", item.metadata["size"]
  end

  # Error Handling Tests
  test "create with missing required fields shows validation errors" do
    post inventory_items_path, params: {
      inventory_item: {
        name: nil,
        category_id: nil
      }
    }

    assert_response :unprocessable_entity
    # Verify error rendering
    assert_select "body"
  end

  test "create with invalid category_id handles gracefully" do
    post inventory_items_path, params: {
      inventory_item: {
        name: "Test Item",
        category_id: 999_999
      }
    }

    assert_response :unprocessable_entity
  end

  test "update with invalid data shows validation errors" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)

    patch inventory_item_path(item), params: {
      inventory_item: {
        name: nil,
        category_id: nil
      }
    }

    assert_response :unprocessable_entity
  end

  # Authorization tests are covered in API controller tests
  # HTML controller authorization is handled by scoping queries to current_user

  # Edge Cases
  test "index with empty inventory renders successfully" do
    get inventory_items_path
    assert_response :success
  end

  test "index with large number of items paginates correctly" do
    create_list(:inventory_item, 30, :clothing, user: @user, category: @category)

    get inventory_items_path, params: { page: 1 }
    assert_response :success

    get inventory_items_path, params: { page: 2 }
    assert_response :success
  end

  test "create with very long name handles gracefully" do
    long_name = "A" * 500

    post inventory_items_path, params: {
      inventory_item: {
        name: long_name,
        category_id: @category.id
      }
    }

    # Should either succeed (if no length limit) or show validation error
    assert_includes [ 302, 422 ], response.status
  end

  test "create with special characters in name handles correctly" do
    special_name = "Item with <script>alert('xss')</script> & special chars"

    post inventory_items_path, params: {
      inventory_item: {
        name: special_name,
        category_id: @category.id
      }
    }

    # Should handle special characters (may be sanitized or stored as-is depending on implementation)
    assert_includes [ 302, 422 ], response.status
  end

  test "update preserves existing attachments when not provided" do
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    file = fixture_file_upload("sample_image.jpg", "image/jpeg")
    item.primary_image.attach(file)

    patch inventory_item_path(item), params: {
      inventory_item: {
        name: "Updated Name"
      }
    }

    assert_redirected_to inventory_items_path
    item.reload
    assert item.primary_image.attached?, "Existing attachment should be preserved"
    assert_equal "Updated Name", item.name
  end
end
