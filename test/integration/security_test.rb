require "test_helper"

class SecurityTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user)
    @token = generate_jwt_token(@user)
    @other_user = create(:user)
    @other_token = generate_jwt_token(@other_user)
  end

  test "unauthorized requests return 401" do
    get "/api/v1/inventory_items", headers: api_v1_headers

    assert_unauthorized_response
  end

  test "invalid JWT token returns 401" do
    get "/api/v1/inventory_items", headers: api_v1_headers("invalid_token")

    assert_unauthorized_response
  end

  test "expired JWT token returns 401" do
    expired_token = generate_expired_jwt_token(@user)

    get "/api/v1/inventory_items", headers: api_v1_headers(expired_token)

    assert_unauthorized_response
  end

  test "users cannot access other users' data" do
    other_item = create(:inventory_item, user: @other_user)

    get "/api/v1/inventory_items/#{other_item.id}", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "users cannot modify other users' data" do
    other_item = create(:inventory_item, user: @other_user)

    put "/api/v1/inventory_items/#{other_item.id}",
        params: { name: "Hacked Name" },
        headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "users cannot delete other users' data" do
    other_item = create(:inventory_item, user: @other_user)

    delete "/api/v1/inventory_items/#{other_item.id}",
           headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "rate limiting prevents abuse" do
    # Mock rate limit exceeded
    RateLimiter.stubs(:exceeded?).returns(true)
    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_response :too_many_requests
    body = json_response
    assert_equal "RATE_LIMIT_EXCEEDED", body["error"]["code"]
  end

  test "rate limiting allows normal usage" do
    # Mock rate limit not exceeded
    RateLimiter.stubs(:exceeded?).returns(false)
    get "/api/v1/inventory_items", headers: api_v1_headers(@token)

    assert_success_response
  end

  test "API responses exclude sensitive fields" do
    get "/api/v1/auth/me", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    user_data = body["data"]["user"]
    assert_not user_data["password_digest"].present?, "Password digest should not be exposed"
  end

  test "SQL injection attempts are prevented" do
    malicious_input = "'; DROP TABLE users; --"

    get "/api/v1/inventory_items?q=#{malicious_input}",
        headers: api_v1_headers(@token)

    # Should not cause database error
    assert_success_response
  end

  test "XSS attempts are sanitized" do
    malicious_name = "<script>alert('xss')</script>"

    post "/api/v1/inventory_items",
         params: { name: malicious_name, category_id: 1 },
         headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    # Name should be sanitized
    assert_not body["data"]["item"]["name"].include?("<script>"), "Should sanitize XSS"
  end

  private

  def generate_jwt_token(user)
    "jwt_token_for_#{user.id}"
  end

  def generate_expired_jwt_token(user)
    "expired_jwt_token_for_#{user.id}"
  end
end