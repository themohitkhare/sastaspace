require "test_helper"

class Api::V1::DocsControllerTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/docs/openapi returns spec" do
    get "/api/v1/docs/openapi"
    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal "3.0.0", body["openapi"]
    assert body["info"].present?
  end
end
