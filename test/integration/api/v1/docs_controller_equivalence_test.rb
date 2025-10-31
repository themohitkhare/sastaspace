require "test_helper"

class Api::V1::DocsControllerEquivalenceTest < ActionDispatch::IntegrationTest
  test "GET /api/v1/docs and /api/v1/docs/openapi return same body" do
    get "/api/v1/docs"
    assert_response :success
    body_a = @response.body

    get "/api/v1/docs/openapi"
    assert_response :success
    body_b = @response.body

    assert_equal body_a, body_b
  end
end
