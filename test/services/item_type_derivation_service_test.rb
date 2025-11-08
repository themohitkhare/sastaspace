require "test_helper"

class ItemTypeDerivationServiceTest < ActiveSupport::TestCase
  test "derive_from_category returns type for top-level category" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name)
    type = ItemTypeDerivationService.derive_from_category(category)
    # Should derive "clothing" from "Tops" category name
    assert_equal "clothing", type
  end

  test "derive_from_category navigates to top-level category" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    parent_category = create(:category, name: unique_name)
    subcategory_name = "T-Shirts #{SecureRandom.hex(4)}"
    subcategory = create(:category, name: subcategory_name, parent_id: parent_category.id)

    type = ItemTypeDerivationService.derive_from_category(subcategory)
    assert_equal "clothing", type
  end

  test "derive_from_category returns nil for nil category" do
    type = ItemTypeDerivationService.derive_from_category(nil)
    assert_nil type
  end

  test "category_type_from_name identifies clothing" do
    type = ItemTypeDerivationService.category_type_from_name("Tops")
    assert_equal "clothing", type
  end

  test "category_type_from_name identifies shoes" do
    type = ItemTypeDerivationService.category_type_from_name("Athletic Shoes")
    assert_equal "shoes", type
  end

  test "category_type_from_name identifies accessories" do
    type = ItemTypeDerivationService.category_type_from_name("Bags")
    assert_equal "accessories", type
  end

  test "category_type_from_name identifies jewelry" do
    type = ItemTypeDerivationService.category_type_from_name("Necklaces")
    assert_equal "jewelry", type
  end

  test "category_type_from_name defaults to clothing" do
    type = ItemTypeDerivationService.category_type_from_name("Unknown Category")
    assert_equal "clothing", type
  end

  test "derive_from_category handles category with parent chain" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    grandparent = create(:category, name: unique_name)
    parent_name = "Shirts #{SecureRandom.hex(4)}"
    parent = create(:category, name: parent_name, parent_id: grandparent.id)
    child_name = "T-Shirts #{SecureRandom.hex(4)}"
    child = create(:category, name: child_name, parent_id: parent.id)

    type = ItemTypeDerivationService.derive_from_category(child)
    assert_equal "clothing", type
  end

  test "category_type_from_name handles case insensitivity" do
    assert_equal "clothing", ItemTypeDerivationService.category_type_from_name("TOPS")
    assert_equal "shoes", ItemTypeDerivationService.category_type_from_name("ATHLETIC SHOES")
    assert_equal "accessories", ItemTypeDerivationService.category_type_from_name("BAGS")
    assert_equal "jewelry", ItemTypeDerivationService.category_type_from_name("NECKLACES")
  end

  test "derive_from_category handles category with parent_category method" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    parent = create(:category, name: unique_name)
    child_name = "T-Shirts #{SecureRandom.hex(4)}"
    child = create(:category, name: child_name, parent_id: parent.id)

    # Mock the parent_category method if it exists
    type = ItemTypeDerivationService.derive_from_category(child)
    assert_equal "clothing", type
  end

  test "category_type_from_name handles various clothing patterns" do
    assert_equal "clothing", ItemTypeDerivationService.category_type_from_name("Pants")
    assert_equal "clothing", ItemTypeDerivationService.category_type_from_name("Dresses")
    assert_equal "clothing", ItemTypeDerivationService.category_type_from_name("Jackets")
  end

  test "category_type_from_name handles various shoe patterns" do
    assert_equal "shoes", ItemTypeDerivationService.category_type_from_name("Boots")
    assert_equal "shoes", ItemTypeDerivationService.category_type_from_name("Sneakers")
    assert_equal "shoes", ItemTypeDerivationService.category_type_from_name("Loafers")
  end

  test "category_type_from_name handles various accessory patterns" do
    assert_equal "accessories", ItemTypeDerivationService.category_type_from_name("Belts")
    assert_equal "accessories", ItemTypeDerivationService.category_type_from_name("Hats")
    assert_equal "accessories", ItemTypeDerivationService.category_type_from_name("Sunglasses")
  end

  test "category_type_from_name handles various jewelry patterns" do
    assert_equal "jewelry", ItemTypeDerivationService.category_type_from_name("Rings")
    assert_equal "jewelry", ItemTypeDerivationService.category_type_from_name("Earrings")
    assert_equal "jewelry", ItemTypeDerivationService.category_type_from_name("Bracelets")
  end

  test "derive_from_category handles category without respond_to parent_id" do
    # Test the branch where category doesn't respond to parent_id
    category_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: category_name)
    # Create a mock that doesn't respond to parent_id
    mock_category = Object.new
    def mock_category.name
      @category_name
    end
    mock_category.instance_variable_set(:@category_name, category_name)
    def mock_category.respond_to?(method)
      method != :parent_id
    end

    type = ItemTypeDerivationService.derive_from_category(mock_category)
    assert_equal "clothing", type
  end

  test "derive_from_category handles category with parent but no parent_id present" do
    unique_name = "Tops #{SecureRandom.hex(4)}"
    category = create(:category, name: unique_name, parent_id: nil)
    type = ItemTypeDerivationService.derive_from_category(category)
    assert_equal "clothing", type
  end

  test "category_type_from_name handles nil name" do
    type = ItemTypeDerivationService.category_type_from_name(nil)
    assert_equal "clothing", type
  end

  test "category_type_from_name handles empty string" do
    type = ItemTypeDerivationService.category_type_from_name("")
    assert_equal "clothing", type
  end
end
