require "test_helper"

class ClothingDetectionServiceFilterTest < ActiveSupport::TestCase
  def setup
    @user = create(:user, gender_preference: "men")
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
  end

  test "filter_by_user_preference shows all items when user prefers unisex" do
    user = create(:user, gender_preference: "unisex")
    service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: user,
      model_name: "qwen3-vl:8b"
    )

    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = service.send(:filter_by_user_preference, items)
    assert_equal 3, filtered.length, "Unisex preference should show all items"
  end

  test "filter_by_user_preference filters to men + unisex when user prefers men" do
    user = create(:user, gender_preference: "men")
    service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: user,
      model_name: "qwen3-vl:8b"
    )

    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = service.send(:filter_by_user_preference, items)
    assert_equal 2, filtered.length, "Men preference should show men + unisex items"
    assert_includes filtered.map { |i| i["gender_styling"] }, "men"
    assert_includes filtered.map { |i| i["gender_styling"] }, "unisex"
    assert_not_includes filtered.map { |i| i["gender_styling"] }, "women"
  end

  test "filter_by_user_preference filters to women + unisex when user prefers women" do
    user = create(:user, gender_preference: "women")
    service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: user,
      model_name: "qwen3-vl:8b"
    )

    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = service.send(:filter_by_user_preference, items)
    assert_equal 2, filtered.length, "Women preference should show women + unisex items"
    assert_includes filtered.map { |i| i["gender_styling"] }, "women"
    assert_includes filtered.map { |i| i["gender_styling"] }, "unisex"
    assert_not_includes filtered.map { |i| i["gender_styling"] }, "men"
  end

  test "filter_by_user_preference returns all items when user has no preference" do
    user = create(:user, gender_preference: nil)
    service = ClothingDetectionService.new(
      image_blob: @image_blob,
      user: user,
      model_name: "qwen3-vl:8b"
    )

    items = [
      { "gender_styling" => "men" },
      { "gender_styling" => "women" },
      { "gender_styling" => "unisex" }
    ]

    filtered = service.send(:filter_by_user_preference, items)
    assert_equal 3, filtered.length, "No preference should show all items"
  end
end
