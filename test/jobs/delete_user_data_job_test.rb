require "test_helper"

class DeleteUserDataJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
  end

  test "performs deletion and removes all user data" do
    # Create user data
    item = create(:inventory_item, user: @user)
    outfit = create(:outfit, user: @user)
    outfit.outfit_items.create!(inventory_item: item)
    analysis = create(:ai_analysis, inventory_item: item)

    user_id = @user.id

    perform_enqueued_jobs do
      DeleteUserDataJob.perform_later(user_id)
    end

    # Verify user is deleted
    assert_nil User.find_by(id: user_id)

    # Verify associated data is deleted
    assert_equal 0, InventoryItem.where(user_id: user_id).count
    assert_equal 0, Outfit.where(user_id: user_id).count
    assert_equal 0, AiAnalysis.where(inventory_item_id: item.id).count
  end

  test "handles already deleted user gracefully" do
    user_id = @user.id
    @user.destroy!

    assert_nothing_raised do
      perform_enqueued_jobs do
        DeleteUserDataJob.perform_later(user_id)
      end
    end
  end

  test "deletes user with images and purges blobs" do
    # Create item with images
    item = create(:inventory_item, user: @user)
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    primary_blob_id = nil
    additional_blob_id = nil

    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "primary.jpg",
        content_type: "image/jpeg"
      )
      primary_blob_id = item.primary_image.blob.id

      item.additional_images.attach(
        io: File.open(test_image_path),
        filename: "additional.jpg",
        content_type: "image/jpeg"
      )
      additional_blob_id = item.additional_images.first.blob.id
    end

    user_id = @user.id

    perform_enqueued_jobs do
      DeleteUserDataJob.perform_later(user_id)
    end

    # Verify user is deleted
    assert_nil User.find_by(id: user_id)

    # Verify blobs are purged
    if File.exist?(test_image_path)
      assert_nil ActiveStorage::Blob.find_by(id: primary_blob_id), "Primary image blob should be purged"
      assert_nil ActiveStorage::Blob.find_by(id: additional_blob_id), "Additional image blob should be purged"
    end
  end

  test "deletes all outfit items before deleting outfits" do
    item1 = create(:inventory_item, user: @user)
    item2 = create(:inventory_item, user: @user)
    outfit = create(:outfit, user: @user)
    outfit_item1 = outfit.outfit_items.create!(inventory_item: item1)
    outfit_item2 = outfit.outfit_items.create!(inventory_item: item2)

    user_id = @user.id
    outfit_id = outfit.id

    perform_enqueued_jobs do
      DeleteUserDataJob.perform_later(user_id)
    end

    # Verify outfit items are deleted
    assert_equal 0, OutfitItem.where(outfit_id: outfit_id).count
    assert_equal 0, Outfit.where(id: outfit_id).count
  end

  test "invalidates all refresh tokens" do
    # Create refresh tokens using the model method
    refresh_token1 = RefreshToken.create_for_user!(@user)
    refresh_token2 = RefreshToken.create_for_user!(@user)
    token1_id = refresh_token1.id
    token2_id = refresh_token2.id

    user_id = @user.id

    perform_enqueued_jobs do
      DeleteUserDataJob.perform_later(user_id)
    end

    # Verify user is deleted (which means tokens are also deleted due to dependent: :destroy)
    assert_nil User.find_by(id: user_id)
    assert_nil RefreshToken.find_by(id: token1_id)
    assert_nil RefreshToken.find_by(id: token2_id)
  end

  test "deletes all AI analyses" do
    item1 = create(:inventory_item, user: @user)
    item2 = create(:inventory_item, user: @user)
    analysis1 = create(:ai_analysis, inventory_item: item1)
    analysis2 = create(:ai_analysis, inventory_item: item2)

    user_id = @user.id

    perform_enqueued_jobs do
      DeleteUserDataJob.perform_later(user_id)
    end

    # Verify analyses are deleted
    assert_equal 0, AiAnalysis.where(id: [ analysis1.id, analysis2.id ]).count
  end
end
