require "test_helper"

class ItemValidationServiceTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @item = build(:inventory_item, user: @user, category: @category)
  end

  test "validate_type_specific_fields validates clothing size" do
    @item.item_type = "clothing"
    @item.size = "XL"
    ItemValidationService.validate_type_specific_fields(@item)
    assert @item.errors.empty?
  end

  test "validate_type_specific_fields rejects invalid clothing size" do
    @item.item_type = "clothing"
    @item.size = "INVALID"
    ItemValidationService.validate_type_specific_fields(@item)
    assert @item.errors[:size].any?
  end

  test "validate_type_specific_fields validates shoe size" do
    @item.item_type = "shoes"
    @item.size = "10"
    ItemValidationService.validate_type_specific_fields(@item)
    assert @item.errors.empty?
  end

  test "validate_type_specific_fields rejects invalid shoe size" do
    @item.item_type = "shoes"
    @item.size = "20" # Too large
    ItemValidationService.validate_type_specific_fields(@item)
    assert @item.errors[:size].any?
  end

  test "validate_item_type_presence adds error when item_type is blank" do
    @item.item_type = nil
    ItemValidationService.validate_item_type_presence(@item)
    assert @item.errors[:item_type].any?
  end

  test "validate_item_type_presence does not add error when item_type is present" do
    @item.item_type = "clothing"
    ItemValidationService.validate_item_type_presence(@item)
    assert @item.errors[:item_type].empty?
  end

  test "valid_clothing_size? returns true for valid sizes" do
    assert ItemValidationService.valid_clothing_size?("M")
    assert ItemValidationService.valid_clothing_size?("XL")
    assert ItemValidationService.valid_clothing_size?("10")
  end

  test "valid_clothing_size? returns false for invalid sizes" do
    assert_not ItemValidationService.valid_clothing_size?("INVALID")
  end

  test "valid_shoe_size? returns true for valid sizes" do
    assert ItemValidationService.valid_shoe_size?("10")
    assert ItemValidationService.valid_shoe_size?("10.5")
  end

  test "valid_shoe_size? returns false for invalid sizes" do
    assert_not ItemValidationService.valid_shoe_size?("20") # Too large
    assert_not ItemValidationService.valid_shoe_size?("1") # Too small
  end

  test "validate_type_specific_fields handles accessories" do
    @item.item_type = "accessories"
    ItemValidationService.validate_type_specific_fields(@item)
    # Should not add errors for accessories
    assert @item.errors.empty?
  end

  test "validate_type_specific_fields handles jewelry" do
    @item.item_type = "jewelry"
    ItemValidationService.validate_type_specific_fields(@item)
    # Should not add errors for jewelry
    assert @item.errors.empty?
  end

  test "valid_clothing_size? returns true for blank size" do
    assert ItemValidationService.valid_clothing_size?(nil)
    assert ItemValidationService.valid_clothing_size?("")
  end

  test "valid_shoe_size? returns true for blank size" do
    assert ItemValidationService.valid_shoe_size?(nil)
    assert ItemValidationService.valid_shoe_size?("")
  end
end
