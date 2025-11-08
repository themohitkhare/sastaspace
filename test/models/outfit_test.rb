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

  test "favorites scope includes outfits with favorite status" do
    user = create(:user)
    fav_status = Outfit.create!(user: user, name: "Fav Status", status: :favorite)
    non_fav = Outfit.create!(user: user, name: "Non Fav", status: :active)

    results = Outfit.favorites
    assert_includes results, fav_status
    assert_not_includes results, non_fav
  end

  test "by_occasion scope filters by occasion" do
    user = create(:user)
    casual = Outfit.create!(user: user, name: "Casual", occasion: "casual")
    formal = Outfit.create!(user: user, name: "Formal", occasion: "formal")

    results = Outfit.by_occasion("casual")
    assert_includes results, casual
    assert_not_includes results, formal
  end

  test "by_season scope filters by season" do
    user = create(:user)
    spring = Outfit.create!(user: user, name: "Spring", season: "spring")
    winter = Outfit.create!(user: user, name: "Winter", season: "winter")

    results = Outfit.by_season("spring")
    assert_includes results, spring
    assert_not_includes results, winter
  end

  test "completeness_score calculates score correctly" do
    user = create(:user)
    category_clothing = create(:category, :clothing)
    category_shoes = create(:category, name: "Shoes #{SecureRandom.hex(4)}")
    category_accessories = create(:category, name: "Bags #{SecureRandom.hex(4)}")

    outfit = Outfit.create!(user: user, name: "Complete Outfit")
    clothing_item = create(:inventory_item, user: user, category: category_clothing, metadata: { color: "blue" })
    shoes_item = create(:inventory_item, user: user, category: category_shoes, metadata: { color: "blue" })
    accessories_item = create(:inventory_item, user: user, category: category_accessories, metadata: { color: "blue" })

    outfit.outfit_items.create!(inventory_item: clothing_item)
    outfit.outfit_items.create!(inventory_item: shoes_item)
    outfit.outfit_items.create!(inventory_item: accessories_item)

    # Should have: clothing (40) + shoes (20) + accessories (20) + coordinated colors (20) = 100
    assert_equal 100, outfit.completeness_score
  end

  test "complete? returns true when score >= 80" do
    user = create(:user)
    category_clothing = create(:category, :clothing)
    category_shoes = create(:category, name: "Shoes #{SecureRandom.hex(4)}")

    outfit = Outfit.create!(user: user, name: "Complete Outfit")
    clothing_item = create(:inventory_item, user: user, category: category_clothing, metadata: { color: "blue" })
    shoes_item = create(:inventory_item, user: user, category: category_shoes, metadata: { color: "blue" })

    outfit.outfit_items.create!(inventory_item: clothing_item)
    outfit.outfit_items.create!(inventory_item: shoes_item)

    # Should have: clothing (40) + shoes (20) + coordinated colors (20) = 80
    assert outfit.complete?
  end

  test "complete? returns false when score < 80" do
    user = create(:user)
    category_clothing = create(:category, :clothing)

    outfit = Outfit.create!(user: user, name: "Incomplete Outfit")
    clothing_item = create(:inventory_item, user: user, category: category_clothing)

    outfit.outfit_items.create!(inventory_item: clothing_item)

    # Should have: clothing (40) = 40 < 80
    assert_not outfit.complete?
  end

  test "worn_count sums outfit_items worn_count" do
    user = create(:user)
    category = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category)
    item2 = create(:inventory_item, user: user, category: category)

    outfit_item1 = outfit.outfit_items.create!(inventory_item: item1, worn_count: 3)
    outfit_item2 = outfit.outfit_items.create!(inventory_item: item2, worn_count: 5)

    assert_equal 8, outfit.worn_count
  end

  test "last_worn_at returns maximum last_worn_at from outfit_items" do
    user = create(:user)
    category = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category)
    item2 = create(:inventory_item, user: user, category: category)

    time1 = 2.days.ago
    time2 = 1.day.ago

    outfit.outfit_items.create!(inventory_item: item1, last_worn_at: time1)
    outfit.outfit_items.create!(inventory_item: item2, last_worn_at: time2)

    # Compare times with a small delta to account for precision differences
    assert_in_delta time2.to_f, outfit.last_worn_at.to_f, 1.0
    assert outfit.last_worn_at > time1
  end

  test "has_clothing_item? returns true when outfit has clothing item" do
    user = create(:user)
    category_clothing = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    clothing_item = create(:inventory_item, user: user, category: category_clothing)

    outfit.outfit_items.create!(inventory_item: clothing_item)

    assert outfit.has_clothing_item?
  end

  test "has_shoes? returns true when outfit has shoes item" do
    user = create(:user)
    category_shoes = create(:category, name: "Shoes #{SecureRandom.hex(4)}")
    outfit = Outfit.create!(user: user, name: "Outfit")
    shoes_item = create(:inventory_item, user: user, category: category_shoes)

    outfit.outfit_items.create!(inventory_item: shoes_item)

    assert outfit.has_shoes?
  end

  test "has_accessories? returns true when outfit has accessories item" do
    user = create(:user)
    category_accessories = create(:category, name: "Bags #{SecureRandom.hex(4)}")
    outfit = Outfit.create!(user: user, name: "Outfit")
    accessories_item = create(:inventory_item, user: user, category: category_accessories)

    outfit.outfit_items.create!(inventory_item: accessories_item)

    assert outfit.has_accessories?
  end

  test "has_coordinated_colors? returns true when items have coordinated colors" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1, metadata: { color: "blue" })
    item2 = create(:inventory_item, user: user, category: category2, metadata: { color: "blue" })

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)

    assert outfit.has_coordinated_colors?
  end

  test "has_coordinated_colors? returns false when items have too many different colors" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    category3 = create(:category, :clothing)
    category4 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1, metadata: { color: "blue" })
    item2 = create(:inventory_item, user: user, category: category2, metadata: { color: "red" })
    item3 = create(:inventory_item, user: user, category: category3, metadata: { color: "green" })
    item4 = create(:inventory_item, user: user, category: category4, metadata: { color: "yellow" })

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)
    outfit.outfit_items.create!(inventory_item: item3)
    outfit.outfit_items.create!(inventory_item: item4)

    assert_not outfit.has_coordinated_colors?
  end

  test "has_coordinated_colors? handles metadata as string" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1)
    item1.update_column(:metadata, '{"color":"blue"}') # Store as string
    item2 = create(:inventory_item, user: user, category: category2)
    item2.update_column(:metadata, '{"color":"blue"}') # Store as string

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)

    assert outfit.has_coordinated_colors?
  end

  test "has_coordinated_colors? handles items without colors" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1, metadata: {})
    item2 = create(:inventory_item, user: user, category: category2, metadata: {})

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)

    assert_not outfit.has_coordinated_colors?
  end

  test "worn_count returns 0 when no outfit_items" do
    user = create(:user)
    outfit = Outfit.create!(user: user, name: "Empty Outfit")

    assert_equal 0, outfit.worn_count
  end

  test "last_worn_at returns nil when no outfit_items" do
    user = create(:user)
    outfit = Outfit.create!(user: user, name: "Empty Outfit")

    assert_nil outfit.last_worn_at
  end

  test "has_coordinated_colors? uses store_accessor color when available" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1)
    item1.color = "blue"
    item1.save!
    item2 = create(:inventory_item, user: user, category: category2)
    item2.color = "blue"
    item2.save!

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)

    assert outfit.has_coordinated_colors?
  end

  test "has_coordinated_colors? handles items with nil color" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1, metadata: { color: nil })
    item2 = create(:inventory_item, user: user, category: category2, metadata: { color: nil })

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)

    assert_not outfit.has_coordinated_colors?
  end

  test "has_coordinated_colors? handles items with exactly 3 unique colors" do
    user = create(:user)
    category1 = create(:category, :clothing)
    category2 = create(:category, :clothing)
    category3 = create(:category, :clothing)
    outfit = Outfit.create!(user: user, name: "Outfit")
    item1 = create(:inventory_item, user: user, category: category1, metadata: { color: "blue" })
    item2 = create(:inventory_item, user: user, category: category2, metadata: { color: "red" })
    item3 = create(:inventory_item, user: user, category: category3, metadata: { color: "green" })

    outfit.outfit_items.create!(inventory_item: item1)
    outfit.outfit_items.create!(inventory_item: item2)
    outfit.outfit_items.create!(inventory_item: item3)

    assert outfit.has_coordinated_colors?
  end
end
