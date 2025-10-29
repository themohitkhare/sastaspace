require "test_helper"

class ToolCallTest < ActiveSupport::TestCase
  def setup
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )

    @user = create(:user)
    @chat = Chat.create!(model: @model, user: @user)
  end

  test "acts_as_tool_call provides necessary methods" do
    tool_call = ToolCall.new(name: "test_tool", arguments: {})

    assert_respond_to tool_call, :name
    assert_respond_to tool_call, :arguments
  end

  test "can create tool_call with name and arguments" do
    tool_call = ToolCall.new(
      name: "generate_image",
      arguments: { "prompt" => "A beautiful sunset", "size" => "1024x1024" }
    )

    assert_equal "generate_image", tool_call.name
    assert_equal "A beautiful sunset", tool_call.arguments["prompt"]
    assert_equal "1024x1024", tool_call.arguments["size"]
  end

  test "tool_call belongs to message" do
    message = @chat.messages.create!(role: "assistant", content: "Test message")
    tool_call = ToolCall.create!(
      message: message,
      name: "test_tool",
      tool_call_id: "call_#{SecureRandom.hex(10)}",
      arguments: {}
    )

    assert_equal message, tool_call.message
  end
end
