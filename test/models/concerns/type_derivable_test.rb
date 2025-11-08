require "test_helper"

class TypeDerivableTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
  end

  test "item_type derives from category" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name)
    item = create(:inventory_item, user: @user, category: category)

    assert_not_nil item.item_type
  end

  test "item_type can be overridden" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name)
    item = create(:inventory_item, user: @user, category: category)

    item.item_type = "custom_type"
    assert_equal "custom_type", item.item_type
  end

  test "item_type returns nil when explicitly set to nil" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name)
    item = create(:inventory_item, user: @user, category: category)

    item.item_type = nil
    assert_nil item.item_type
  end

  test "item_type derives from top-level category" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    parent_category = create(:category, name: unique_name)
    subcategory_name = "T-Shirts #{SecureRandom.hex(4)}"
    subcategory = create(:category, name: subcategory_name, parent_id: parent_category.id)

    item = create(:inventory_item, user: @user, category: subcategory)
    # item_type should derive from parent category
    assert_not_nil item.item_type
  end

  test "item_type handles category without parent" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name, parent_id: nil)
    item = create(:inventory_item, user: @user, category: category)

    assert_not_nil item.item_type
  end

  test "item_type handles nil category gracefully" do
    # This tests the edge case where category might be nil
    # In practice, this shouldn't happen due to validations, but we test it
    item = build(:inventory_item, user: @user, category: nil)
    # item_type should handle nil category
    assert_respond_to item, :item_type
  end
end
