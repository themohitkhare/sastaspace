require "test_helper"

class Api::V1::DocsControllerShowTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/docs returns OpenAPI spec envelope" do
    get "/api/v1/docs"
    assert_response :success
    body = JSON.parse(@response.body)
    assert_equal "3.0.0", body["openapi"]
    assert_equal "SastaSpace API", body.dig("info", "title")
    assert body.key?("paths")
  end
end
