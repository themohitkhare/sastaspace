require "test_helper"

class OutfitItemTest < ActiveSupport::TestCase
  # Validations
  test "validates presence of outfit" do
    outfit_item = build(:outfit_item, outfit: nil)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:outfit], "must exist"
  end

  test "validates presence of clothing item" do
    outfit_item = build(:outfit_item, clothing_item: nil)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:clothing_item], "must exist"
  end

  test "validates numericality of position" do
    outfit_item = build(:outfit_item, position: -1)
    assert_not outfit_item.valid?
    assert_includes outfit_item.errors[:position], "must be greater than 0"
  end

  # Uniqueness
  test "clothing item can only be in outfit once" do
    outfit = create(:outfit)
    clothing_item = create(:clothing_item, user: outfit.user)

    create(:outfit_item, outfit: outfit, clothing_item: clothing_item)

    duplicate_item = build(:outfit_item, outfit: outfit, clothing_item: clothing_item)
    assert_not duplicate_item.valid?, "Should not allow duplicate clothing item in same outfit"
    assert_includes duplicate_item.errors[:clothing_item], "has already been taken"
  end

  test "same clothing item can be in different outfits" do
    outfit1 = create(:outfit)
    outfit2 = create(:outfit, user: outfit1.user)
    clothing_item = create(:clothing_item, user: outfit1.user)

    outfit_item1 = create(:outfit_item, outfit: outfit1, clothing_item: clothing_item)
    outfit_item2 = create(:outfit_item, outfit: outfit2, clothing_item: clothing_item)

    assert outfit_item1.valid?
    assert outfit_item2.valid?
  end

  # Scopes
  test "by_position scope orders by position" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)
    item3 = create(:clothing_item, user: outfit.user)

    outfit_item1 = create(:outfit_item, outfit: outfit, clothing_item: item1, position: 3)
    outfit_item2 = create(:outfit_item, outfit: outfit, clothing_item: item2, position: 1)
    outfit_item3 = create(:outfit_item, outfit: outfit, clothing_item: item3, position: 2)

    ordered_items = OutfitItem.by_position

    assert_equal [ outfit_item2, outfit_item3, outfit_item1 ], ordered_items.to_a
  end

  test "by_category scope filters by clothing item category" do
    outfit = create(:outfit)
    top_item = create(:clothing_item, user: outfit.user, category: "top")
    bottom_item = create(:clothing_item, user: outfit.user, category: "bottom")

    top_outfit_item = create(:outfit_item, outfit: outfit, clothing_item: top_item)
    bottom_outfit_item = create(:outfit_item, outfit: outfit, clothing_item: bottom_item)

    top_items = OutfitItem.by_category("top")
    assert_includes top_items, top_outfit_item
    assert_not_includes top_items, bottom_outfit_item
  end

  # Methods
  test "move_to_position updates position and reorders others" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)
    item3 = create(:clothing_item, user: outfit.user)

    outfit_item1 = create(:outfit_item, outfit: outfit, clothing_item: item1, position: 1)
    outfit_item2 = create(:outfit_item, outfit: outfit, clothing_item: item2, position: 2)
    outfit_item3 = create(:outfit_item, outfit: outfit, clothing_item: item3, position: 3)

    outfit_item2.move_to_position(1)

    outfit_item1.reload
    outfit_item2.reload
    outfit_item3.reload

    assert_equal 1, outfit_item2.position, "Moved item should be at position 1"
    assert_equal 2, outfit_item1.position, "First item should move to position 2"
    assert_equal 3, outfit_item3.position, "Third item should stay at position 3"
  end

  test "move_to_position handles edge cases" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)

    outfit_item1 = create(:outfit_item, outfit: outfit, clothing_item: item1, position: 1)
    outfit_item2 = create(:outfit_item, outfit: outfit, clothing_item: item2, position: 2)

    # Move to same position
    outfit_item1.move_to_position(1)
    outfit_item1.reload
    assert_equal 1, outfit_item1.position, "Should stay at same position"

    # Move to last position
    outfit_item1.move_to_position(2)
    outfit_item1.reload
    outfit_item2.reload
    assert_equal 2, outfit_item1.position, "Should move to last position"
    assert_equal 1, outfit_item2.position, "Other item should move up"
  end

  test "swap_positions swaps positions of two items" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)

    outfit_item1 = create(:outfit_item, outfit: outfit, clothing_item: item1, position: 1)
    outfit_item2 = create(:outfit_item, outfit: outfit, clothing_item: item2, position: 2)

    outfit_item1.swap_positions(outfit_item2)

    outfit_item1.reload
    outfit_item2.reload

    assert_equal 2, outfit_item1.position, "First item should move to position 2"
    assert_equal 1, outfit_item2.position, "Second item should move to position 1"
  end

  # Callbacks
  test "auto-assigns position if not provided" do
    outfit = create(:outfit)
    clothing_item = create(:clothing_item, user: outfit.user)

    outfit_item = OutfitItem.create(outfit: outfit, clothing_item: clothing_item)

    assert outfit_item.position.present?, "Should auto-assign position"
    assert outfit_item.position > 0, "Position should be positive"
  end

  test "auto-increments position for new items" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)

    outfit_item1 = create(:outfit_item, outfit: outfit, clothing_item: item1)
    outfit_item2 = create(:outfit_item, outfit: outfit, clothing_item: item2)

    assert outfit_item2.position > outfit_item1.position, "Second item should have higher position"
  end

  test "validates clothing item belongs to same user as outfit" do
    outfit = create(:outfit)
    other_user_item = create(:clothing_item)

    outfit_item = build(:outfit_item, outfit: outfit, clothing_item: other_user_item)

    assert_not outfit_item.valid?, "Should not be valid"
    assert_includes outfit_item.errors[:clothing_item], "must belong to the same user as the outfit"
  end
end
