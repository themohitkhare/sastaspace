require "test_helper"

class OutfitTest < ActiveSupport::TestCase
  test "should be valid with required attributes" do
    user = create(:user)
    outfit = Outfit.new(user: user, name: "Weekend Look")
    assert outfit.valid?
  end

  test "name should be present" do
    outfit = Outfit.new(user: create(:user), name: nil)
    assert_not outfit.valid?
    assert_includes outfit.errors[:name], "can't be blank"
  end

  # Associations to outfit_items/inventory_items are defined but underlying
  # join table for inventory items isn't available in the current schema.
  # Validation and scope behaviors are tested instead.

  test "favorites scope returns only favorite outfits" do
    user = create(:user)
    fav = Outfit.create!(user: user, name: "Fav", is_favorite: true)
    non = Outfit.create!(user: user, name: "Non", is_favorite: false)

    results = Outfit.favorites
    assert_includes results, fav
    assert_not_includes results, non
  end
end
