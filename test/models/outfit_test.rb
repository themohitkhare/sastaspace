require "test_helper"

class OutfitTest < ActiveSupport::TestCase
  # Validations
  test "validates presence of name" do
    outfit = build(:outfit, name: nil)
    assert_not outfit.valid?
    assert_includes outfit.errors[:name], "can't be blank"
  end

  test "validates presence of user" do
    outfit = build(:outfit, user: nil)
    assert_not outfit.valid?
    assert_includes outfit.errors[:user], "must exist"
  end

  test "validates inclusion of occasion" do
    outfit = build(:outfit, occasion: "invalid_occasion")
    assert_not outfit.valid?
    assert_includes outfit.errors[:occasion], "is not included in the list"
  end

  test "validates inclusion of season" do
    outfit = build(:outfit, season: "invalid_season")
    assert_not outfit.valid?
    assert_includes outfit.errors[:season], "is not included in the list"
  end

  # Associations
  test "belongs to user" do
    user = create(:user)
    outfit = create(:outfit, user: user)
    assert_equal user, outfit.user
  end

  test "has many outfit items" do
    outfit = create(:outfit)
    item = create(:clothing_item, user: outfit.user)
    outfit_item = create(:outfit_item, outfit: outfit, clothing_item: item)
    assert_includes outfit.outfit_items, outfit_item
  end

  test "has many clothing items through outfit items" do
    outfit = create(:outfit)
    item = create(:clothing_item, user: outfit.user)
    create(:outfit_item, outfit: outfit, clothing_item: item)
    assert_includes outfit.clothing_items, item
  end

  # Scopes
  test "by_occasion scope filters by occasion" do
    casual_outfit = create(:outfit, :casual)
    formal_outfit = create(:outfit, :formal)

    casual_outfits = Outfit.by_occasion("casual")
    assert_includes casual_outfits, casual_outfit
    assert_not_includes casual_outfits, formal_outfit
  end

  test "by_season scope filters by season" do
    summer_outfit = create(:outfit, :summer)
    winter_outfit = create(:outfit, :winter)

    summer_outfits = Outfit.by_season("summer")
    assert_includes summer_outfits, summer_outfit
    assert_not_includes summer_outfits, winter_outfit
  end

  test "favorites scope returns only favorite outfits" do
    favorite_outfit = create(:outfit, :favorite)
    regular_outfit = create(:outfit)

    favorites = Outfit.favorites
    assert_includes favorites, favorite_outfit
    assert_not_includes favorites, regular_outfit
  end

  test "public scope returns only public outfits" do
    public_outfit = create(:outfit, :public)
    private_outfit = create(:outfit)

    public_outfits = Outfit.public_outfits
    assert_includes public_outfits, public_outfit
    assert_not_includes public_outfits, private_outfit
  end

  test "with_items scope returns outfits with clothing items" do
    outfit_with_items = create(:outfit, :with_items)
    empty_outfit = create(:outfit)

    outfits_with_items = Outfit.with_items
    assert_includes outfits_with_items, outfit_with_items
    assert_not_includes outfits_with_items, empty_outfit
  end

  # Methods
  test "add_clothing_item adds item to outfit" do
    outfit = create(:outfit)
    clothing_item = create(:clothing_item, user: outfit.user)

    outfit_item = outfit.add_clothing_item(clothing_item)

    assert outfit_item.persisted?, "Should create outfit item"
    assert_equal outfit, outfit_item.outfit
    assert_equal clothing_item, outfit_item.clothing_item
    assert_includes outfit.clothing_items, clothing_item
  end

  test "add_clothing_item with position" do
    outfit = create(:outfit)
    clothing_item = create(:clothing_item, user: outfit.user)

    outfit_item = outfit.add_clothing_item(clothing_item, position: 5)

    assert_equal 5, outfit_item.position
  end

  test "remove_clothing_item removes item from outfit" do
    outfit = create(:outfit, :with_items)
    clothing_item = outfit.clothing_items.first

    outfit.remove_clothing_item(clothing_item)

    assert_not_includes outfit.clothing_items, clothing_item
  end

  test "has_clothing_item checks if item is in outfit" do
    outfit = create(:outfit, :with_items)
    clothing_item = outfit.clothing_items.first
    other_item = create(:clothing_item, user: outfit.user)

    assert outfit.has_clothing_item?(clothing_item), "Should have the item"
    assert_not outfit.has_clothing_item?(other_item), "Should not have other item"
  end

  test "items_by_category groups items by category" do
    outfit = create(:outfit)
    top = create(:clothing_item, user: outfit.user, category: "top")
    bottom = create(:clothing_item, user: outfit.user, category: "bottom")
    shoes = create(:clothing_item, user: outfit.user, category: "shoes")

    outfit.add_clothing_item(top)
    outfit.add_clothing_item(bottom)
    outfit.add_clothing_item(shoes)

    items_by_category = outfit.items_by_category

    assert_includes items_by_category["top"], top
    assert_includes items_by_category["bottom"], bottom
    assert_includes items_by_category["shoes"], shoes
  end

  test "total_estimated_cost calculates sum of item prices" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user, price: 50.0)
    item2 = create(:clothing_item, user: outfit.user, price: 75.0)

    outfit.add_clothing_item(item1)
    outfit.add_clothing_item(item2)

    assert_equal 125.0, outfit.total_estimated_cost
  end

  test "total_estimated_cost handles items without prices" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user, price: 50.0)
    item2 = create(:clothing_item, user: outfit.user, price: nil)

    outfit.add_clothing_item(item1)
    outfit.add_clothing_item(item2)

    assert_equal 50.0, outfit.total_estimated_cost
  end

  test "duplicate creates copy of outfit" do
    original_outfit = create(:outfit, :with_items)
    new_user = create(:user)

    duplicated_outfit = original_outfit.duplicate(new_user)

    assert duplicated_outfit.persisted?, "Should create new outfit"
    assert_equal new_user, duplicated_outfit.user
    assert_equal original_outfit.name + " (Copy)", duplicated_outfit.name
    assert_equal original_outfit.occasion, duplicated_outfit.occasion
    assert_equal original_outfit.season, duplicated_outfit.season
  end

  test "duplicate copies outfit items" do
    original_outfit = create(:outfit, :with_items)
    new_user = create(:user)

    duplicated_outfit = original_outfit.duplicate(new_user)

    assert_equal original_outfit.clothing_items.count, duplicated_outfit.clothing_items.count
  end

  # Callbacks
  test "sets default position for outfit items" do
    outfit = create(:outfit)
    item1 = create(:clothing_item, user: outfit.user)
    item2 = create(:clothing_item, user: outfit.user)

    outfit_item1 = outfit.add_clothing_item(item1)
    outfit_item2 = outfit.add_clothing_item(item2)

    assert outfit_item1.position.present?, "Should set position for first item"
    assert outfit_item2.position.present?, "Should set position for second item"
    assert outfit_item2.position > outfit_item1.position, "Should increment positions"
  end

  test "validates clothing items belong to same user" do
    outfit = create(:outfit)
    other_user_item = create(:clothing_item)

    assert_raises(ActiveRecord::RecordInvalid) do
      outfit.add_clothing_item(other_user_item)
    end
  end
end
