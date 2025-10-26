require "test_helper"

class RubyllmChatTest < ActionDispatch::IntegrationTest
  setup do
    # Ensure we have at least one model available for testing
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
  end

  test "can view chat index" do
    chat = Chat.create!(model: @model)

    get chats_path

    assert_response :success
  end

  test "can show a chat with messages" do
    chat = Chat.create!(model: @model)

    # Add a test message
    chat.messages.create!(role: "user", content: "Test message")

    get chat_path(chat)

    assert_response :success
  end

  test "chat has model association" do
    chat = Chat.create!(model: @model)

    assert_equal @model, chat.model
    assert chat.model_id.present?
  end

  test "messages belong to chat" do
    chat = Chat.create!(model: @model)
    message = chat.messages.create!(role: "user", content: "Hello")

    assert_equal chat, message.chat
    assert_includes chat.messages, message
  end

  test "acts_as_chat provides ask method" do
    chat = Chat.create!(model: @model)

    # This should not raise an error (even if API key is not set)
    assert_respond_to chat, :ask
  end
end
