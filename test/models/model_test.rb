require "test_helper"

class ModelTest < ActiveSupport::TestCase
  def setup
    @model = Model.first_or_create!(
      name: "gpt-4o-mini",
      provider: "openai",
      model_id: "gpt-4o-mini",
      context_window: 128_000
    )
  end

  test "model is valid" do
    assert @model.valid?
  end

  test "acts_as_model provides necessary methods" do
    # Verify acts_as_model functionality
    assert_respond_to @model, :name
    assert_respond_to @model, :provider
    assert_respond_to @model, :model_id
  end

  test "can create model with provider and model_id" do
    model = Model.create!(
      name: "claude-3-haiku",
      provider: "anthropic",
      model_id: "claude-3-haiku-20240307",
      context_window: 200_000
    )

    assert_equal "anthropic", model.provider
    assert_equal "claude-3-haiku-20240307", model.model_id
    assert_equal 200_000, model.context_window
  end

  test "model has chats association" do
    user = create(:user)
    chat = Chat.create!(model: @model, user: user)

    assert_includes @model.chats, chat
  end
end
