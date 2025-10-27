require "test_helper"

class RefreshTokenTest < ActiveSupport::TestCase
  test "requires token" do
    user = create(:user)
    refresh_token = RefreshToken.new(user: user, expires_at: 30.days.from_now)

    assert_not refresh_token.valid?
    assert_includes refresh_token.errors[:token], "can't be blank"
  end

  test "requires unique token" do
    user = create(:user)
    token = RefreshToken.generate_token

    RefreshToken.create!(user: user, token: token, expires_at: 30.days.from_now)

    duplicate = RefreshToken.new(user: user, token: token, expires_at: 30.days.from_now)
    assert_not duplicate.valid?
    assert_includes duplicate.errors[:token], "has already been taken"
  end

  test "requires expires_at" do
    user = create(:user)
    refresh_token = RefreshToken.new(user: user, token: RefreshToken.generate_token)

    assert_not refresh_token.valid?
    assert_includes refresh_token.errors[:expires_at], "can't be blank"
  end

  test "can be created for a user" do
    user = create(:user)

    refresh_token = RefreshToken.create_for_user!(user)

    assert refresh_token.persisted?
    assert_equal user, refresh_token.user
    assert refresh_token.token.present?
    assert_not refresh_token.blacklisted?
  end

  test "active scope returns non-blacklisted, non-expired tokens" do
    user = create(:user)

    active_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.from_now,
      blacklisted: false
    )

    expired_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.ago,
      blacklisted: false
    )

    blacklisted_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.from_now,
      blacklisted: true
    )

    active = RefreshToken.active.to_a
    assert_includes active, active_token
    assert_not_includes active, expired_token
    assert_not_includes active, blacklisted_token
  end

  test "active? returns true for valid token" do
    user = create(:user)
    refresh_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.from_now,
      blacklisted: false
    )

    assert refresh_token.active?
  end

  test "active? returns false for expired token" do
    user = create(:user)
    refresh_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.ago,
      blacklisted: false
    )

    assert_not refresh_token.active?
  end

  test "active? returns false for blacklisted token" do
    user = create(:user)
    refresh_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.from_now,
      blacklisted: true
    )

    assert_not refresh_token.active?
  end

  test "blacklist! marks token as blacklisted" do
    user = create(:user)
    refresh_token = RefreshToken.create!(
      user: user,
      token: RefreshToken.generate_token,
      expires_at: 1.hour.from_now,
      blacklisted: false
    )

    refresh_token.blacklist!

    assert refresh_token.blacklisted?
  end

  test "generate_token creates unique tokens" do
    tokens = 10.times.map { RefreshToken.generate_token }

    assert_equal tokens.uniq.length, tokens.length, "All tokens should be unique"
  end
end
