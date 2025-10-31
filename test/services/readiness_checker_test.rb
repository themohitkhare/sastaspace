require "test_helper"

class ReadinessCheckerTest < ActiveSupport::TestCase
  test "check_all returns ready when all checks pass" do
    checker = ReadinessChecker.new
    ActiveRecord::Base.connection.stubs(:execute).returns([ [ 1 ] ])
    Rails.cache.stubs(:write).returns(true)
    Rails.cache.stubs(:read).returns("pong")
    ActiveStorage::Blob.stubs(:count).returns(0)

    result = checker.check_all

    assert result[:ready]
    assert_equal "ok", result[:checks][:database][:status]
    assert_equal "ok", result[:checks][:cache][:status]
    assert_equal "ok", result[:checks][:storage][:status]
  end

  test "check_all handles errors gracefully" do
    checker = ReadinessChecker.new
    ActiveRecord::Base.connection.stubs(:execute).raises(StandardError.new("db error"))
    Rails.cache.stubs(:write).raises(StandardError.new("cache error"))
    ActiveStorage::Blob.stubs(:count).raises(StandardError.new("storage error"))

    result = checker.check_all

    refute result[:ready]
    assert_equal "error", result[:checks][:database][:status]
    assert_equal "error", result[:checks][:cache][:status]
    assert_equal "error", result[:checks][:storage][:status]
  end
end
