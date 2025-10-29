require "test_helper"
require "rack/test"

class RequestIdMiddlewareTest < ActiveSupport::TestCase
  include Rack::Test::Methods

  def app
    inner_app = lambda do |env|
      [ 200, { "Content-Type" => "text/plain" }, [ env["REQUEST_ID"] || "" ] ]
    end
    RequestIdMiddleware.new(inner_app)
  end

  test "sets X-Request-ID header and env when not provided" do
    get "/"
    assert last_response.ok?

    request_id = last_response.headers["X-Request-ID"]
    assert request_id.present?
    assert_match(/[0-9a-f\-]{36}/i, request_id)
    assert_equal request_id, last_response.body
  end

  test "preserves provided X-Request-ID" do
    provided = "123e4567-e89b-12d3-a456-426614174000"
    header "X-Request-ID", provided
    get "/"
    assert_equal provided, last_response.headers["X-Request-ID"]
    assert_equal provided, last_response.body
  end
end
