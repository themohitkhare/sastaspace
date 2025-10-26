require "test_helper"

class ChatTest < ActiveSupport::TestCase
  setup do
    # Ensure we have at least one model available for testing
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
  end

  test "can create a chat with model" do
    chat = Chat.create!(model: @model)

    assert_not_nil chat.id
    assert_equal @model, chat.model
    assert chat.model_id.present?
  end

  test "chat has messages association" do
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

  test "can add messages to chat" do
    chat = Chat.create!(model: @model)

    message1 = chat.messages.create!(role: "user", content: "First message")
    message2 = chat.messages.create!(role: "assistant", content: "Response")

    assert_equal 2, chat.messages.count
    assert chat.messages.include?(message1)
    assert chat.messages.include?(message2)
  end
end
