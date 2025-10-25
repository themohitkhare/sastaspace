require "test_helper"

class TagTest < ActiveSupport::TestCase
  def setup
    @tag = build(:tag)
  end

  test "should be valid" do
    assert @tag.valid?
  end

  test "name should be present" do
    @tag.name = nil
    assert_not @tag.valid?
    assert_includes @tag.errors[:name], "can't be blank"
  end

  test "name should be unique" do
    @tag.save!
    duplicate_tag = build(:tag, name: @tag.name)
    assert_not duplicate_tag.valid?
    assert_includes duplicate_tag.errors[:name], "has already been taken"
  end

  test "should have default color" do
    tag = create(:tag, color: nil)
    assert_equal '#3B82F6', tag.color
  end
end
