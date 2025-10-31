require "test_helper"

class ReadinessCheckerDetailsTest < ActiveSupport::TestCase
  test "check_all includes durations for ok checks" do
    checker = ReadinessChecker.new
    result = checker.check_all
    assert_includes result, :ready
    %i[database cache storage].each do |key|
      check = result[:checks][key]
      assert_equal "ok", check[:status]
      assert check[:duration_ms].is_a?(Numeric)
    end
  end

  test "safe_check returns error structure when block raises" do
    checker = ReadinessChecker.new
    err = checker.send(:safe_check) { raise "boom" }
    assert_equal "error", err[:status]
    assert_match /boom/, err[:error]
  end
end
