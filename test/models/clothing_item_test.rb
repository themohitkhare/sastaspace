require "test_helper"

class ClothingItemTest < ActiveSupport::TestCase
  # Validations
  test "validates presence of name" do
    item = build(:clothing_item, name: nil)
    assert_not item.valid?
    assert_includes item.errors[:name], "can't be blank"
  end

  test "validates presence of category" do
    item = build(:clothing_item, category: nil)
    assert_not item.valid?
    assert_includes item.errors[:category], "can't be blank"
  end

  test "validates presence of user" do
    item = build(:clothing_item, user: nil)
    assert_not item.valid?
    assert_includes item.errors[:user], "must exist"
  end

  test "validates inclusion of category" do
    item = build(:clothing_item, category: "invalid_category")
    assert_not item.valid?
    assert_includes item.errors[:category], "is not included in the list"
  end

  test "validates inclusion of season" do
    item = build(:clothing_item, season: "invalid_season")
    assert_not item.valid?
    assert_includes item.errors[:season], "is not included in the list"
  end

  test "validates inclusion of occasion" do
    item = build(:clothing_item, occasion: "invalid_occasion")
    assert_not item.valid?
    assert_includes item.errors[:occasion], "is not included in the list"
  end

  # Associations
  test "belongs to user" do
    user = create(:user)
    item = create(:clothing_item, user: user)
    assert_equal user, item.user
  end

  test "has many outfit items" do
    item = create(:clothing_item)
    outfit = create(:outfit, user: item.user)
    outfit_item = create(:outfit_item, outfit: outfit, clothing_item: item)
    assert_includes item.outfit_items, outfit_item
  end

  test "has many outfits through outfit items" do
    item = create(:clothing_item)
    outfit = create(:outfit, user: item.user)
    create(:outfit_item, outfit: outfit, clothing_item: item)
    assert_includes item.outfits, outfit
  end

  test "has many ai analyses" do
    item = create(:clothing_item)
    analysis = create(:ai_analysis, clothing_item: item)
    assert_includes item.ai_analyses, analysis
  end

  test "has one attached photo" do
    item = create(:clothing_item)
    assert item.respond_to?(:photo)
  end

  # Scopes
  test "by_category scope filters by category" do
    top = create(:clothing_item, category: "top")
    bottom = create(:clothing_item, category: "bottom")

    tops = ClothingItem.by_category("top")
    assert_includes tops, top
    assert_not_includes tops, bottom
  end

  test "by_season scope filters by season" do
    summer_item = create(:clothing_item, :summer)
    winter_item = create(:clothing_item, :winter)

    summer_items = ClothingItem.by_season("summer")
    assert_includes summer_items, summer_item
    assert_not_includes summer_items, winter_item
  end

  test "by_occasion scope filters by occasion" do
    casual_item = create(:clothing_item, :casual)
    formal_item = create(:clothing_item, :formal)

    casual_items = ClothingItem.by_occasion("casual")
    assert_includes casual_items, casual_item
    assert_not_includes casual_items, formal_item
  end

  test "with_photos scope returns only items with photos" do
    item_with_photo = create(:clothing_item, :with_photo)
    item_without_photo = create(:clothing_item)

    items_with_photos = ClothingItem.with_photos
    assert_includes items_with_photos, item_with_photo
    assert_not_includes items_with_photos, item_without_photo
  end

  # Photo validation
  test "photo must be a valid image format" do
    item = build(:clothing_item)

    # Valid image
    item.photo.attach(
      io: StringIO.new("fake_image_data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )
    assert item.valid?

    # Invalid format
    item.photo.attach(
      io: StringIO.new("fake_data"),
      filename: "test.txt",
      content_type: "text/plain"
    )
    assert_not item.valid?
    assert_includes item.errors[:photo], "must be an image"
  end

  test "photo size must be under 10MB" do
    item = build(:clothing_item)

    # Mock large file
    large_file = StringIO.new("x" * (11.megabytes))
    item.photo.attach(
      io: large_file,
      filename: "large.jpg",
      content_type: "image/jpeg"
    )

    assert_not item.valid?
    assert_includes item.errors[:photo], "must be less than 10MB"
  end

  # Methods
  test "photo_url returns URL for photo attachment" do
    item = create(:clothing_item, :with_photo)

    assert item.photo_url.present?, "Should return photo URL"
    assert item.photo_url.include?("rails/active_storage"), "Should be Active Storage URL"
  end

  test "photo_url returns nil when no photo attached" do
    item = create(:clothing_item)

    assert_nil item.photo_url, "Should return nil when no photo"
  end

  test "thumbnail_url returns thumbnail variant URL" do
    item = create(:clothing_item, :with_photo)

    assert item.thumbnail_url.present?, "Should return thumbnail URL"
    assert item.thumbnail_url.include?("thumbnail"), "Should be thumbnail variant"
  end

  test "search_by_name finds items by name" do
    blue_shirt = create(:clothing_item, name: "Blue Cotton Shirt")
    red_pants = create(:clothing_item, name: "Red Denim Pants")

    results = ClothingItem.search_by_name("blue")
    assert_includes results, blue_shirt
    assert_not_includes results, red_pants
  end

  test "search_by_name is case insensitive" do
    item = create(:clothing_item, name: "Blue Cotton Shirt")

    results = ClothingItem.search_by_name("BLUE")
    assert_includes results, item
  end

  # Callbacks
  test "generates image hash when photo is attached" do
    item = create(:clothing_item, :with_photo)

    assert item.image_hash.present?, "Should generate image hash"
    assert item.image_hash.length == 64, "Should be SHA256 hash"
  end

  test "updates image hash when photo changes" do
    item = create(:clothing_item, :with_photo)
    original_hash = item.image_hash

    # Attach different photo
    item.photo.attach(
      io: StringIO.new("different_image_data"),
      filename: "different.jpg",
      content_type: "image/jpeg"
    )
    item.save!

    assert item.image_hash != original_hash, "Image hash should change"
  end
end
