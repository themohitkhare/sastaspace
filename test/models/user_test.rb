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
    assert_includes user.errors[:password], "is too short (minimum is 8 characters)"
  end

  test "validates password strength - requires uppercase letter" do
    user = build(:user, password: "lowercase123")
    assert_not user.valid?
    assert user.errors[:password].any? { |e| e.include?("uppercase") || e.include?("format") }
  end

  test "validates password strength - requires lowercase letter" do
    user = build(:user, password: "UPPERCASE123")
    assert_not user.valid?
    assert user.errors[:password].any? { |e| e.include?("lowercase") || e.include?("format") }
  end

  test "validates password strength - requires number" do
    user = build(:user, password: "NoNumbers")
    assert_not user.valid?
    assert user.errors[:password].any? { |e| e.include?("number") || e.include?("format") }
  end

  test "accepts password with uppercase, lowercase, and number" do
    user = build(:user, password: "ValidPass123", password_confirmation: "ValidPass123")
    assert user.valid?, "Password should be valid with uppercase, lowercase, and number"
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
  test "has many inventory items" do
    user = create(:user)
    item = create(:inventory_item, :clothing, user: user)
    assert_includes user.inventory_items, item
  end

  test "has many ai analyses" do
    user = create(:user)
    item = create(:inventory_item, :clothing, user: user)
    analysis = create(:ai_analysis, inventory_item: item)
    assert_includes user.ai_analyses, analysis
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

    user = build(:user, first_name: nil, last_name: nil)
    assert_equal user.email, user.full_name
  end
end
