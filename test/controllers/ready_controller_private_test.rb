require "test_helper"

class ReadyControllerPrivateTest < ActiveSupport::TestCase
  test "safe_check returns error when block raises" do
    controller = ReadyController.new
    result = controller.send(:safe_check) { raise "boom" }
    assert_equal "error", result[:status]
    assert_match /boom/, result[:error]
  end

  test "check_readiness aggregates checks and sets ready false when any fails" do
    controller = ReadyController.new
    controller.stubs(:check_migrations).returns({ status: "ok", duration_ms: 1.0 })
    controller.stubs(:check_queues).returns({ status: "error", error: "q" })
    controller.stubs(:check_storage).returns({ status: "ok", duration_ms: 1.0 })
    result = controller.send(:check_readiness)
    assert_equal false, result[:ready]
    assert_equal %i[migrations queues storage], result[:checks].keys
  end
end


