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
end
