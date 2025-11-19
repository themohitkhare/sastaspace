require "test_helper"

class ReadyControllerUnitTest < ActionDispatch::IntegrationTest
  test "check_migrations returns error on exception" do
    controller = ReadyController.new
    ActiveRecord::Base.connection.stubs(:execute).raises(StandardError.new("db error"))
    result = controller.send(:check_migrations)
    assert_equal "error", result[:status]
    assert_match /db error/, result[:error]
  end

  test "check_queues returns error on exception" do
    controller = ReadyController.new
    # Stub Sidekiq.redis to raise an error
    if defined?(Sidekiq)
      Sidekiq.stubs(:redis).raises(StandardError.new("redis down"))
    else
      Redis.stubs(:new).raises(StandardError.new("redis down"))
    end
    result = controller.send(:check_queues)
    assert_equal "error", result[:status]
    assert_match /redis down|down/, result[:error]
  end

  test "check_storage returns ok with duration" do
    controller = ReadyController.new
    result = controller.send(:check_storage)
    assert_equal "ok", result[:status]
    assert result[:duration_ms].is_a?(Numeric)
  end
end
