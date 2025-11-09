require "test_helper"

class Api::V1::AccountLockoutTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user, password: "Password123!")
    @ip_address = "192.168.1.1"

    # Disable rate limiting for account lockout tests
    # These tests need to make multiple login attempts to test lockout behavior
    ENV["DISABLE_RATE_LIMITING"] = "true"
    # Reload rack-attack to pick up the change
    load Rails.root.join("config/initializers/rack_attack.rb") if defined?(Rack::Attack)
  end

  teardown do
    ENV.delete("DISABLE_RATE_LIMITING")
    # Reload rack-attack to restore normal behavior
    load Rails.root.join("config/initializers/rack_attack.rb") if defined?(Rack::Attack)
  end

  test "account locks after max failed login attempts" do
    max_attempts = FailedLoginAttempt::MAX_ATTEMPTS

    # Make max failed attempts (should lock account)
    max_attempts.times do
      post "/api/v1/auth/login",
           params: { email: @user.email, password: "wrong" }.to_json,
           headers: api_v1_headers
    end

    # Account should now be locked - even correct password should fail
    post "/api/v1/auth/login",
         params: { email: @user.email, password: "Password123!" }.to_json,
         headers: api_v1_headers

    assert_response :too_many_requests
    body = json_response
    assert_not body["success"]
    assert_equal "ACCOUNT_LOCKED", body["error"]["code"]
  end

  test "account unlocks after lockout duration" do
    # Lock account
    FailedLoginAttempt::MAX_ATTEMPTS.times do
      post "/api/v1/auth/login",
           params: { email: @user.email, password: "wrong" }.to_json,
           headers: api_v1_headers
    end

    # Verify locked
    post "/api/v1/auth/login",
         params: { email: @user.email, password: "Password123!" }.to_json,
         headers: api_v1_headers
    assert_response :too_many_requests

    # Travel forward past lockout duration
    travel FailedLoginAttempt::LOCKOUT_DURATION + 1.minute do
      post "/api/v1/auth/login",
           params: { email: @user.email, password: "Password123!" }.to_json,
           headers: api_v1_headers

      assert_response :ok
      body = json_response
      assert body["success"]
    end
  end

  test "successful login clears failed attempts" do
    # Make some failed attempts
    3.times do
      post "/api/v1/auth/login",
           params: { email: @user.email, password: "wrong" }.to_json,
           headers: api_v1_headers
    end

    assert_equal 3, FailedLoginAttempt.for_user(@user).count

    # Successful login
    post "/api/v1/auth/login",
         params: { email: @user.email, password: "Password123!" }.to_json,
         headers: api_v1_headers

    assert_response :ok
    assert_equal 0, FailedLoginAttempt.for_user(@user).count
  end

  private

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!("Authorization" => "Bearer #{token}") if token
    headers
  end

  def json_response
    JSON.parse(@response.body)
  end
end
