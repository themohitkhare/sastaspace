require "test_helper"

class ReadinessCheckerHelpersTest < ActiveSupport::TestCase
  test "monotonic_ms returns a numeric value" do
    checker = ReadinessChecker.new
    t = checker.send(:monotonic_ms)
    assert t.is_a?(Numeric)
  end

  test "ok_with_duration returns ok status with duration" do
    checker = ReadinessChecker.new
    result = checker.send(:ok_with_duration, checker.send(:monotonic_ms))
    assert_equal "ok", result[:status]
    assert result[:duration_ms].is_a?(Numeric)
  end

  test "error_with returns error status with message" do
    checker = ReadinessChecker.new
    result = checker.send(:error_with, StandardError.new("oops"))
    assert_equal "error", result[:status]
    assert_match /oops/, result[:error]
  end
end
