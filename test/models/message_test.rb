require "test_helper"

class MessageTest < ActiveSupport::TestCase
  def setup
    # Create model for chat
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )

    # Create user for chat
    @user = create(:user)

    # Create chat
    @chat = Chat.create!(model: @model, user: @user)
  end

  test "message belongs to chat" do
    message = @chat.messages.create!(role: "user", content: "Test message")

    assert_equal @chat, message.chat
  end

  test "message has role attribute" do
    message = @chat.messages.create!(role: "user", content: "Test message")

    assert_equal "user", message.role
  end

  test "message has content attribute" do
    message = @chat.messages.create!(role: "user", content: "Test message")

    assert_equal "Test message", message.content
  end

  test "message has attachments association" do
    message = @chat.messages.create!(role: "user", content: "Test message")

    # Test that attachments association exists
    assert_respond_to message, :attachments
    assert_equal 0, message.attachments.count
  end

  test "acts_as_message provides necessary methods" do
    message = @chat.messages.create!(role: "user", content: "Test")

    # Verify acts_as_message functionality
    assert_respond_to message, :role
    assert_respond_to message, :content
  end

  test "can create message with different roles" do
    user_message = @chat.messages.create!(role: "user", content: "User message")
    assistant_message = @chat.messages.create!(role: "assistant", content: "Assistant message")

    assert_equal "user", user_message.role
    assert_equal "assistant", assistant_message.role
  end
end
