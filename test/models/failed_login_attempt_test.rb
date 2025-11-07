require "test_helper"

class FailedLoginAttemptTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @ip_address = "192.168.1.1"
  end

  test "records failed login attempt" do
    assert_difference "FailedLoginAttempt.count", 1 do
      FailedLoginAttempt.record_failure(@user.email, @ip_address)
    end

    attempt = FailedLoginAttempt.last
    assert_equal @user.id, attempt.user_id
    assert_equal @ip_address, attempt.ip_address
    assert attempt.failed_at.present?
  end

  test "account_locked? returns false for no attempts" do
    assert_not FailedLoginAttempt.account_locked?(@user.email, @ip_address)
  end

  test "account_locked? returns true after max attempts" do
    # Create max attempts
    FailedLoginAttempt::MAX_ATTEMPTS.times do
      FailedLoginAttempt.record_failure(@user.email, @ip_address)
    end

    assert FailedLoginAttempt.account_locked?(@user.email, @ip_address)
  end

  test "account_locked? resets after lockout duration" do
    # Create max attempts
    FailedLoginAttempt::MAX_ATTEMPTS.times do
      FailedLoginAttempt.record_failure(@user.email, @ip_address)
    end

    assert FailedLoginAttempt.account_locked?(@user.email, @ip_address)

    # Travel forward past lockout duration
    travel FailedLoginAttempt::LOCKOUT_DURATION + 1.minute do
      assert_not FailedLoginAttempt.account_locked?(@user.email, @ip_address)
    end
  end

  test "clear_for_user removes all attempts for user" do
    FailedLoginAttempt.record_failure(@user.email, @ip_address)
    FailedLoginAttempt.record_failure(@user.email, @ip_address)

    assert_difference "FailedLoginAttempt.count", -2 do
      FailedLoginAttempt.clear_for_user(@user)
    end
  end

  test "clear_for_ip removes all attempts for IP" do
    FailedLoginAttempt.record_failure(@user.email, @ip_address)
    FailedLoginAttempt.record_failure("other@example.com", @ip_address)

    assert_difference "FailedLoginAttempt.count", -2 do
      FailedLoginAttempt.clear_for_ip(@ip_address)
    end
  end
end
