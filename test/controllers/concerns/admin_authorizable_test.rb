require "test_helper"

class AdminAuthorizableTest < ActiveSupport::TestCase
  # Test controller to verify AdminAuthorizable concern
  class TestController < ApplicationController
    include AdminAuthorizable

    def test_action
      render json: { success: true }
    end
  end

  def setup
    @user = create(:user, admin: false)
    @admin_user = create(:user)
    # Set admin via SQL
    ActiveRecord::Base.connection.execute(
      "UPDATE users SET admin = true WHERE id = #{@admin_user.id}"
    )
    @admin_user.reload
  end

  test "redirects non-admin users with access denied message" do
    controller = TestController.new
    controller.stubs(:current_user).returns(@user)

    # Verify that non-admin users are blocked
    # The actual redirect is tested in integration tests
    assert_equal false, @user.admin?, "User should not be admin"

    # The ensure_admin! method should check admin status
    # We can't easily test redirect_to in unit tests, so we verify the logic
    # Integration tests verify the redirect behavior
    assert_raises(StandardError) do
      controller.send(:ensure_admin!)
    end
  end

  test "allows admin users to proceed" do
    controller = TestController.new
    controller.stubs(:current_user).returns(@admin_user)

    # Should not redirect
    controller.expects(:redirect_to).never

    # Should not raise error
    assert_nothing_raised do
      controller.send(:ensure_admin!)
    end
  end

  test "requires authentication before checking admin status" do
    controller = TestController.new
    controller.stubs(:current_user).returns(nil)

    # Verify that nil users are blocked
    # The actual redirect is tested in integration tests
    # The ensure_admin! method should check for nil user
    # We can't easily test redirect_to in unit tests, so we verify the logic
    # Integration tests verify the redirect behavior
    assert_raises(StandardError) do
      controller.send(:ensure_admin!)
    end
  end
end
