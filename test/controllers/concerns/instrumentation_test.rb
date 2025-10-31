require "test_helper"

class InstrumentationTest < ActionDispatch::IntegrationTest
  # Test Instrumentation concern through a real controller
  setup do
    @user = create(:user)
    # Use UpController as it's simple and includes Instrumentation via ApplicationController
    UpController.any_instance.stubs(:authenticate_user!).returns(true)
  end

  test "instrument_request publishes request.started notification" do
    notifications = []
    ActiveSupport::Notifications.subscribe("request.started") do |*args|
      notifications << ActiveSupport::Notifications::Event.new(*args)
    end

    get "/up"

    assert_equal 1, notifications.length
    event = notifications.first
    assert_equal "request.started", event.name
    assert_equal "UpController", event.payload[:controller]
    assert_equal "show", event.payload[:action]
  end

  test "instrument_request publishes request.completed notification" do
    notifications = []
    ActiveSupport::Notifications.subscribe("request.completed") do |*args|
      notifications << ActiveSupport::Notifications::Event.new(*args)
    end

    get "/up"

    assert_equal 1, notifications.length
    event = notifications.first
    assert_equal "request.completed", event.name
    assert_equal "UpController", event.payload[:controller]
    assert_equal 200, event.payload[:status]
    assert event.payload[:duration_ms].is_a?(Numeric)
  end

  test "instrument_request publishes request.failed notification on error" do
    notifications = []
    ActiveSupport::Notifications.subscribe("request.failed") do |*args|
      notifications << ActiveSupport::Notifications::Event.new(*args)
    end

    # Stub an action to raise an error
    UpController.any_instance.stubs(:show).raises(StandardError.new("Test error"))

    assert_raises(StandardError) do
      get "/up"
    end

    assert_equal 1, notifications.length
    event = notifications.first
    assert_equal "request.failed", event.name
    assert_equal "StandardError", event.payload[:error]
    assert_equal "Test error", event.payload[:error_message]
  end

  test "instrument_request includes user_id when user is authenticated" do
    UpController.any_instance.stubs(:current_user).returns(@user)

    notifications = []
    ActiveSupport::Notifications.subscribe("request.completed") do |*args|
      notifications << ActiveSupport::Notifications::Event.new(*args)
    end

    get "/up"

    event = notifications.first
    assert_equal @user.id, event.payload[:user_id]
  end
end

