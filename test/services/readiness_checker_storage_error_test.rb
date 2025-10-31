require "test_helper"

class ReadinessCheckerStorageErrorTest < ActiveSupport::TestCase
  test "check_storage returns error structure on exception" do
    checker = ReadinessChecker.new
    ActiveStorage::Blob.stubs(:count).raises(StandardError.new("storage down"))
    result = checker.send(:check_storage)
    assert_equal "error", result[:status]
    assert_match /storage down/, result[:error]
  end
end
