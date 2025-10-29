require "test_helper"

class JsonWebTokenTest < ActiveSupport::TestCase
  test "encodes and decodes access token" do
    payload = { user_id: 123 }
    token = Auth::JsonWebToken.encode_access_token(payload.dup)

    decoded = Auth::JsonWebToken.decode(token)
    assert_equal 123, decoded[:user_id]
    assert decoded[:exp].present?
  end

  test "encodes and decodes refresh token" do
    payload = { user_id: 99 }
    token = Auth::JsonWebToken.encode_refresh_token(payload.dup)
    decoded = Auth::JsonWebToken.decode(token)
    assert_equal 99, decoded[:user_id]
  end

  test "raises ExpiredToken for expired token" do
    token = Auth::JsonWebToken.encode({ user_id: 1 }, exp: 1.second.ago)
    assert_raises(ExceptionHandler::ExpiredToken) do
      Auth::JsonWebToken.decode(token)
    end
  end

  test "raises InvalidToken for bad token" do
    assert_raises(ExceptionHandler::InvalidToken) do
      Auth::JsonWebToken.decode("this.is.not.valid")
    end
  end
end
