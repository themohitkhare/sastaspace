require "test_helper"

class InstrumentationTest < ActionDispatch::IntegrationTest
  # Test Instrumentation concern through UpController
  # UpController doesn't require authentication, so we can test directly
  setup do
    @user = create(:user)
    @subscribers = []
  end

  teardown do
    # Clean up any remaining subscribers
    @subscribers.each { |sub| ActiveSupport::Notifications.unsubscribe(sub) if sub }
    @subscribers.clear

    # Unstub to prevent interference with other tests
    ApplicationController.any_instance.unstub(:authenticate_user!) rescue nil
    ApplicationController.any_instance.unstub(:current_user) rescue nil
    UpController.any_instance.unstub(:show) rescue nil
  end

  test "instrument_request publishes request.started notification" do
    notifications = []
    # Subscribe to request.started notification specifically
    # The callback receives: name, start, finish, id, payload
    subscriber = ActiveSupport::Notifications.subscribe("request.started") do |*args|
      event = ActiveSupport::Notifications::Event.new(*args)
      notifications << { name: event.name, payload: event.payload }
    end
    @subscribers << subscriber

    # Make actual request
    get "/up"

    # Ensure response was successful (meaning around_action executed)
    assert_response :success

    # Unsubscribe after request completes
    ActiveSupport::Notifications.unsubscribe(subscriber)
    @subscribers.delete(subscriber)

    # Check for request.started notification
    assert_not_empty notifications, "Should have received at least one notification. Instrumentation may not be working."
    started_notification = notifications.find { |n| n[:name] == "request.started" }
    assert_not_nil started_notification,
                   "Should have received request.started notification. Received: #{notifications.map { |n| n[:name] }.inspect}"
    assert_equal "UpController", started_notification[:payload][:controller]
    assert_equal "show", started_notification[:payload][:action]
  end

  test "instrument_request publishes request.completed notification" do
    notifications = []
    subscriber = ActiveSupport::Notifications.subscribe("request.completed") do |*args|
      event = ActiveSupport::Notifications::Event.new(*args)
      notifications << { name: event.name, payload: event.payload }
    end
    @subscribers << subscriber

    get "/up"

    # Ensure response was successful
    assert_response :success

    # Unsubscribe after request completes
    ActiveSupport::Notifications.unsubscribe(subscriber)
    @subscribers.delete(subscriber)

    # Check for request.completed notification
    assert_not_empty notifications, "Should have received at least one notification"
    completed_notification = notifications.find { |n| n[:name] == "request.completed" }
    assert_not_nil completed_notification,
                   "Should have received request.completed notification. Received: #{notifications.map { |n| n[:name] }.inspect}"
    assert_equal "UpController", completed_notification[:payload][:controller]
    assert_equal 200, completed_notification[:payload][:status]
    assert completed_notification[:payload][:duration_ms].is_a?(Numeric)
  end

  test "instrument_request publishes request.failed notification on error" do
    notifications = []
    subscriber = ActiveSupport::Notifications.subscribe("request.failed") do |*args|
      event = ActiveSupport::Notifications::Event.new(*args)
      notifications << { name: event.name, payload: event.payload }
    end
    @subscribers << subscriber

    # Stub the show action to raise an error when called
    original_show = UpController.instance_method(:show)
    UpController.define_method(:show) do
      raise StandardError, "Test error"
    end

    # In integration tests, Rails catches exceptions and renders error pages
    # The error will be caught by around_action, notification published, then re-raised
    # Rails will then render the error page (500 response)
    begin
      get "/up"
      # If we get here, Rails handled the exception (which is normal in integration tests)
      # The important thing is that the notification was published
    rescue StandardError => e
      # If exception propagates, that's also fine - notification should still be published
      assert_equal "Test error", e.message
    ensure
      # Restore original show method
      UpController.define_method(:show, original_show)
    end

    # Unsubscribe after request completes
    ActiveSupport::Notifications.unsubscribe(subscriber)
    @subscribers.delete(subscriber)

    # Check for request.failed notification - this is the key assertion
    assert_not_empty notifications, "Should have received at least one notification"
    failed_notification = notifications.find { |n| n[:name] == "request.failed" }
    assert_not_nil failed_notification,
                   "Should have received request.failed notification. Received: #{notifications.map { |n| n[:name] }.inspect}"
    assert_equal "StandardError", failed_notification[:payload][:error]
    assert_equal "Test error", failed_notification[:payload][:error_message]
  end

  test "instrument_request includes user_id when user is authenticated" do
    # Stub current_user to return the user
    ApplicationController.any_instance.stubs(:current_user).returns(@user)

    notifications = []
    subscriber = ActiveSupport::Notifications.subscribe("request.completed") do |*args|
      event = ActiveSupport::Notifications::Event.new(*args)
      notifications << { name: event.name, payload: event.payload }
    end
    @subscribers << subscriber

    get "/up"

    # Ensure response was successful
    assert_response :success

    # Unsubscribe after request completes
    ActiveSupport::Notifications.unsubscribe(subscriber)
    @subscribers.delete(subscriber)

    # Check for request.completed notification
    assert_not_empty notifications, "Should have received at least one notification"
    completed_notification = notifications.find { |n| n[:name] == "request.completed" }
    assert_not_nil completed_notification,
                   "Should have received request.completed notification. Received: #{notifications.map { |n| n[:name] }.inspect}"
    assert_equal @user.id, completed_notification[:payload][:user_id]
  end
end
