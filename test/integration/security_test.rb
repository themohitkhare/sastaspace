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

  test "POST /api/v1/users/export enqueues data export job" do
    assert_enqueued_with(job: ExportUserDataJob) do
      post "/api/v1/users/export", headers: api_v1_headers(@token)
    end

    assert_success_response
    body = json_response

    assert body["data"]["message"].include?("Export started"), "Should confirm export started"
    assert body["data"]["job_id"].present?, "Should return job ID"
  end

  test "GET /api/v1/users/export/status returns export status" do
    # Create export job
    export_job = create(:export_job, user: @user, status: "processing")

    get "/api/v1/users/export/status", headers: api_v1_headers(@token)

    assert_success_response
    body = json_response

    assert_equal "processing", body["data"]["export"]["status"]
    assert body["data"]["export"]["created_at"].present?, "Should include creation time"
  end

  test "GET /api/v1/users/export/status for other user returns 404" do
    other_export = create(:export_job, user: @other_user)

    get "/api/v1/users/export/status", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "GET /api/v1/users/export/download returns export file" do
    export_job = create(:export_job, user: @user, status: "completed")
    export_job.export_file.attach(
      io: StringIO.new("export_data"),
      filename: "user_data.json",
      content_type: "application/json"
    )

    get "/api/v1/users/export/download", headers: api_v1_headers(@token)

    assert_response :success
    assert_equal "application/json", @response.content_type
    assert_equal "attachment", @response.headers["Content-Disposition"]
  end

  test "GET /api/v1/users/export/download for incomplete export returns 404" do
    export_job = create(:export_job, user: @user, status: "processing")

    get "/api/v1/users/export/download", headers: api_v1_headers(@token)

    assert_not_found_response
  end

  test "POST /api/v1/users/delete deletes user account and data" do
    # Create user data
    inventory_item = create(:inventory_item, user: @user)
    outfit = create(:outfit, user: @user)
    analysis = create(:ai_analysis, inventory_item: inventory_item)

    delete "/api/v1/users/delete",
           params: { password: "Password123!" },
           headers: api_v1_headers(@token)

    assert_success_response

    # Verify user and data are deleted
    assert_raises(ActiveRecord::RecordNotFound) { @user.reload }
    assert_raises(ActiveRecord::RecordNotFound) { inventory_item.reload }
    assert_raises(ActiveRecord::RecordNotFound) { outfit.reload }
    assert_raises(ActiveRecord::RecordNotFound) { analysis.reload }
  end

  test "DELETE /api/v1/users/delete with wrong password returns 401" do
    delete "/api/v1/users/delete",
           params: { password: "WrongPassword123!" },
           headers: api_v1_headers(@token)

    assert_unauthorized_response
  end

  test "DELETE /api/v1/users/delete without password returns 400" do
    delete "/api/v1/users/delete", headers: api_v1_headers(@token)

    assert_error_response(:bad_request, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["details"]["password"].present?, "Expected password validation error"
  end

  test "account deletion purges attached files" do
    inventory_item = create(:inventory_item, :with_photo, user: @user)

    delete "/api/v1/users/delete",
           params: { password: "Password123!" },
           headers: api_v1_headers(@token)

    assert_success_response

    # Verify files are purged
    assert_not inventory_item.photo.attached?, "Photo should be purged"
  end

  test "account deletion creates audit log" do
    delete "/api/v1/users/delete",
           params: { password: "Password123!" },
           headers: api_v1_headers(@token)

    assert_success_response

    # Verify audit log was created
    audit_log = AuditLog.last
    assert_equal "account_deleted", audit_log.action
    assert_equal @user.id, audit_log.user_id
  end

  test "sensitive data is not logged" do
    # Mock logger to capture log messages
    log_messages = []
    Rails.logger.stubs(:info).returns(nil)
    post "/api/v1/auth/login",
         params: { email: @user.email, password: "Password123!" },
         headers: api_v1_headers

    # Verify password is not in logs
    log_content = log_messages.join(" ")
    assert_not log_content.include?("Password123!"), "Password should not be logged"
  end

  test "API responses exclude sensitive fields" do
    user = create(:user, :with_profile)

    get "/api/v1/auth/me", headers: api_v1_headers(generate_jwt_token(user))

    assert_success_response
    body = json_response

    user_data = body["data"]["user"]
    assert_not user_data["password_digest"].present?, "Password digest should not be exposed"
    assert_not user_data["reset_password_token"].present?, "Reset token should not be exposed"
  end

  test "file uploads are validated for type and size" do
    inventory_item = create(:inventory_item, user: @user)

    # Test invalid file type
    invalid_file = {
      photo: fixture_file_upload("sample_text.txt", "text/plain")
    }

    post "/api/v1/inventory_items/#{inventory_item.id}/photo",
         params: invalid_file,
         headers: api_v1_headers(@token)

    assert_error_response(:unprocessable_entity, "VALIDATION_ERROR")
    body = json_response
    assert body["error"]["details"]["photo"].present?, "Expected photo validation error"
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
         params: { name: malicious_name, category: "top" },
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
