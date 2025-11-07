require "test_helper"

class Api::V1::UsersGdprTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper
  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
  end

  test "POST /api/v1/users/export initiates data export" do
    post "/api/v1/users/export",
         headers: api_v1_headers(@token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["job_id"].present?
    assert_equal "processing", body["data"]["status"]
  end

  test "GET /api/v1/users/export/status returns job status" do
    # First initiate export
    post "/api/v1/users/export",
         headers: api_v1_headers(@token)
    job_id = json_response["data"]["job_id"]

    # Perform the job synchronously for test
    perform_enqueued_jobs

    # Check status (should be completed after job runs)
    get "/api/v1/users/export/status",
        params: { job_id: job_id },
        headers: api_v1_headers(@token)

    assert_response :success
    body = json_response
    assert body["success"]
    assert_includes %w[processing completed], body["data"]["status"]
  end

  test "GET /api/v1/users/export/status requires job_id" do
    get "/api/v1/users/export/status",
        headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "MISSING_JOB_ID", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete requires password confirmation" do
    delete "/api/v1/users/delete",
           headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "CONFIRMATION_REQUIRED", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete with invalid password returns error" do
    delete "/api/v1/users/delete",
           params: { password: "wrong_password" }.to_json,
           headers: api_v1_headers(@token)

    assert_response :unauthorized
    body = json_response
    assert_not body["success"]
    assert_equal "INVALID_PASSWORD", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete with valid password initiates deletion" do
    password = "Password123!"
    user = create(:user, password: password)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    delete "/api/v1/users/delete",
           params: { password: password }.to_json,
           headers: api_v1_headers(token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["message"].present?
  end

  test "GDPR endpoints require authentication" do
    post "/api/v1/users/export"
    assert_response :unauthorized

    get "/api/v1/users/export/status", params: { job_id: "test" }
    assert_response :unauthorized

    delete "/api/v1/users/delete", params: { password: "test" }.to_json
    assert_response :unauthorized
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
