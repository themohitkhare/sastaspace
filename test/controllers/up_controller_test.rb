require "test_helper"

class UpControllerTest < ActionDispatch::IntegrationTest
  test "returns up status" do
    get "/up"

    assert_response :success
    body = JSON.parse(response.body)
    assert_equal "up", body["status"]
    assert body["timestamp"].present?
  end
end
