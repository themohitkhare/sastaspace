require "test_helper"

class UserTest < ActiveSupport::TestCase
  # Validations
  test "validates presence of email" do
    user = build(:user, email: nil)
    assert_not user.valid?
    assert_includes user.errors[:email], "can't be blank"
  end

  test "validates uniqueness of email" do
    create(:user, email: "test@example.com")
    user = build(:user, email: "test@example.com")
    assert_not user.valid?
    assert_includes user.errors[:email], "has already been taken"
  end

  test "validates presence of password" do
    user = build(:user, password: nil)
    assert_not user.valid?
    assert_includes user.errors[:password], "can't be blank"
  end

  test "validates password length" do
    user = build(:user, password: "short")
    assert_not user.valid?
    assert_includes user.errors[:password], "is too short"
  end

  # Password validation
  test "password must contain at least one uppercase letter" do
    user = build(:user, password: "password123!")
    assert_not user.valid?
    assert_includes user.errors[:password], "must contain at least one uppercase letter"
  end

  test "password must contain at least one lowercase letter" do
    user = build(:user, password: "PASSWORD123!")
    assert_not user.valid?
    assert_includes user.errors[:password], "must contain at least one lowercase letter"
  end

  test "password must contain at least one number" do
    user = build(:user, password: "Password!")
    assert_not user.valid?
    assert_includes user.errors[:password], "must contain at least one number"
  end

  test "password must contain at least one special character" do
    user = build(:user, password: "Password123")
    assert_not user.valid?
    assert_includes user.errors[:password], "must contain at least one special character"
  end

  # Password hashing
  test "password is hashed when user is created" do
    password = "Password123!"
    user = create(:user, password: password)

    assert_not_equal password, user.password_digest
    assert user.authenticate(password)
    assert_not user.authenticate("wrong_password")
  end

  # Associations
  test "has many clothing items" do
    user = create(:user)
    item = create(:clothing_item, user: user)
    assert_includes user.clothing_items, item
  end

  test "has many outfits" do
    user = create(:user)
    outfit = create(:outfit, user: user)
    assert_includes user.outfits, outfit
  end

  test "has many ai analyses" do
    user = create(:user)
    item = create(:clothing_item, user: user)
    analysis = create(:ai_analysis, clothing_item: item)
    assert_includes user.ai_analyses, analysis
  end

  test "has one user profile" do
    user = create(:user)
    profile = create(:user_profile, user: user)
    assert_equal profile, user.user_profile
  end

  # Scopes
  test "confirmed scope returns only confirmed users" do
    confirmed_user = create(:user, :confirmed)
    unconfirmed_user = create(:user)

    confirmed_users = User.confirmed

    assert_includes confirmed_users, confirmed_user
    assert_not_includes confirmed_users, unconfirmed_user
  end

  # Methods
  test "full_name returns first and last name" do
    user = build(:user, first_name: "John", last_name: "Doe")
    assert_equal "John Doe", user.full_name
  end

  test "full_name handles missing names gracefully" do
    user = build(:user, first_name: nil, last_name: "Doe")
    assert_equal "Doe", user.full_name

    user = build(:user, first_name: "John", last_name: nil)
    assert_equal "John", user.full_name
  end
end
