require "test_helper"

class ApplicationCable::ConnectionTest < ActionCable::Connection::TestCase
  test "connection can be established" do
    connect

    assert connection
  end

  test "connection can be disconnected" do
    connect

    assert connection

    disconnect

    # Connection should be closed
    assert_nil connection
  end

  test "connection handles basic WebSocket connection" do
    connect

    assert_not_nil connection
    # Connection is established if it's not nil
    assert connection.present?
  end
end
