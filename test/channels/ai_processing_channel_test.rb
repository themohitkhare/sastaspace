require "test_helper"

class AiProcessingChannelTest < ActionCable::Channel::TestCase
  setup do
    @user = create(:user)
  end

  test "subscribes to detection updates with user_id" do
    subscribe(user_id: @user.id)

    assert subscription.confirmed?
    assert_has_stream "detection_#{@user.id}"
  end

  test "subscribes to extraction updates with analysis_id" do
    analysis = create(:clothing_analysis, user: @user)
    subscribe(analysis_id: analysis.id)

    assert subscription.confirmed?
    assert_has_stream "extraction_#{analysis.id}"
  end

  test "subscribes to both detection and extraction updates" do
    analysis = create(:clothing_analysis, user: @user)
    subscribe(user_id: @user.id, analysis_id: analysis.id)

    assert subscription.confirmed?
    assert_has_stream "detection_#{@user.id}"
    assert_has_stream "extraction_#{analysis.id}"
  end

  test "rejects subscription without user_id or analysis_id" do
    subscribe

    assert subscription.rejected?
  end

  test "rejects subscription with empty params" do
    subscribe(user_id: nil, analysis_id: nil)

    assert subscription.rejected?
  end

  test "unsubscribes cleanly" do
    subscribe(user_id: @user.id)

    assert subscription.confirmed?

    unsubscribe

    # Should not raise any errors
    assert_nothing_raised do
      unsubscribe
    end
  end

  test "can receive broadcasts on detection channel" do
    subscribe(user_id: @user.id)

    assert_broadcasts "detection_#{@user.id}", 1 do
      ActionCable.server.broadcast("detection_#{@user.id}", { type: "test" })
    end
  end

  test "can receive broadcasts on extraction channel" do
    analysis = create(:clothing_analysis, user: @user)
    subscribe(analysis_id: analysis.id)

    assert_broadcasts "extraction_#{analysis.id}", 1 do
      ActionCable.server.broadcast("extraction_#{analysis.id}", { type: "test" })
    end
  end
end
