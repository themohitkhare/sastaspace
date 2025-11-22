require "test_helper"

class AdminConstraintTest < ActiveSupport::TestCase
  setup do
    @constraint = AdminConstraint.new
    @admin_user = create(:user)
    # Use raw SQL to bypass attr_readonly
    ActiveRecord::Base.connection.execute(
      "UPDATE users SET admin = true WHERE id = #{@admin_user.id}"
    )
    @admin_user.reload
    @regular_user = create(:user)
  end

  test "matches returns true for admin user with session" do
    request = mock_request_with_session(@admin_user.id)
    assert @constraint.matches?(request), "Should match for admin user"
  end

  test "matches returns false for non-admin user with session" do
    request = mock_request_with_session(@regular_user.id)
    assert_not @constraint.matches?(request), "Should not match for non-admin user"
  end

  test "matches returns false when session has no user_id" do
    request = mock_request_with_session(nil)
    assert_not @constraint.matches?(request), "Should not match without user_id"
  end

  test "matches returns false when user not found" do
    request = mock_request_with_session(99999) # Non-existent user ID
    assert_not @constraint.matches?(request), "Should not match for non-existent user"
  end

  test "matches handles request without session" do
    request = Rack::MockRequest.env_for("/")
    request_obj = Rack::Request.new(request)

    assert_not @constraint.matches?(request_obj), "Should not match without session"
  end

  test "matches works with JWT token in cookies for admin" do
    token = Auth::JsonWebToken.encode({ user_id: @admin_user.id })
    request = mock_request_with_cookie("access_token", token)

    assert @constraint.matches?(request), "Should match for admin with valid JWT"
  end

  test "matches works with signed JWT cookie for admin" do
    token = Auth::JsonWebToken.encode({ user_id: @admin_user.id })

    # Manually sign the token like Rails does
    key_generator = ActiveSupport::KeyGenerator.new(
      Rails.application.secret_key_base,
      iterations: 1000
    )
    secret = key_generator.generate_key("signed cookie")
    verifier = ActiveSupport::MessageVerifier.new(secret, serializer: Marshal, digest: "SHA1")
    signed_token = verifier.generate(token)

    request = mock_request_with_cookie("access_token", signed_token)

    assert @constraint.matches?(request), "Should match for admin with signed JWT"
  end

  test "matches returns false with invalid JWT token" do
    request = mock_request_with_cookie("access_token", "invalid_token")

    assert_not @constraint.matches?(request), "Should not match with invalid JWT"
  end

  test "matches returns false with expired JWT token" do
    # Create an expired token manually to ensure it's actually expired
    expired_payload = { user_id: @admin_user.id, exp: 1.hour.ago.to_i }
    expired_token = JWT.encode(expired_payload, Auth::JsonWebToken::SECRET_KEY)
    request = mock_request_with_cookie("access_token", expired_token)

    assert_not @constraint.matches?(request), "Should not match with expired JWT"
  end

  test "matches returns false for non-admin user with JWT" do
    token = Auth::JsonWebToken.encode({ user_id: @regular_user.id })
    request = mock_request_with_cookie("access_token", token)

    assert_not @constraint.matches?(request), "Should not match for non-admin with JWT"
  end

  test "session takes precedence over JWT" do
    # Session has regular user, JWT has admin user
    token = Auth::JsonWebToken.encode({ user_id: @admin_user.id })
    request = mock_request_with_session_and_cookie(@regular_user.id, "access_token", token)

    # Should use session (regular user) and return false
    assert_not @constraint.matches?(request), "Session should take precedence over JWT"
  end

  test "falls back to JWT when session is empty" do
    token = Auth::JsonWebToken.encode({ user_id: @admin_user.id })
    env = Rack::MockRequest.env_for("/", "HTTP_COOKIE" => "access_token=#{token}")
    env["rack.session"] = {}
    request = Rack::Request.new(env)

    assert @constraint.matches?(request), "Should fall back to JWT when session is empty"
  end

  private

  def mock_request_with_session(user_id)
    env = Rack::MockRequest.env_for("/")
    env["rack.session"] = { user_id: user_id }
    Rack::Request.new(env)
  end

  def mock_request_with_cookie(key, value)
    env = Rack::MockRequest.env_for("/", "HTTP_COOKIE" => "#{key}=#{value}")
    env["rack.session"] = {}
    Rack::Request.new(env)
  end

  def mock_request_with_session_and_cookie(user_id, cookie_key, cookie_value)
    env = Rack::MockRequest.env_for("/", "HTTP_COOKIE" => "#{cookie_key}=#{cookie_value}")
    env["rack.session"] = { user_id: user_id }
    Rack::Request.new(env)
  end
end
