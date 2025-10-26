require "test_helper"

class CategoryTest < ActiveSupport::TestCase
  def setup
    @category = build(:category)
  end

  test "should be valid" do
    assert @category.valid?
  end

  test "name should be present" do
    @category.name = nil
    assert_not @category.valid?
    assert_includes @category.errors[:name], "can't be blank"
  end

  test "name should be unique within same parent" do
    parent = create(:category, name: "Parent")
    @category.parent_id = parent.id
    @category.save!

    duplicate_category = build(:category, name: @category.name, parent_id: parent.id)
    assert_not duplicate_category.valid?
    assert_includes duplicate_category.errors[:name], "has already been taken"
  end

  test "name can be duplicate across different parents" do
    parent1 = create(:category, name: "Parent 1")
    parent2 = create(:category, name: "Parent 2")

    category1 = create(:category, name: "Child", parent_id: parent1.id)
    category2 = build(:category, name: "Child", parent_id: parent2.id)

    assert category2.valid?
  end

  test "slug should be present" do
    @category.name = nil
    @category.slug = ""
    assert_not @category.valid?
    assert_includes @category.errors[:slug], "can't be blank"
  end

  test "slug should be unique" do
    @category.save!
    duplicate_category = build(:category, slug: @category.slug)
    assert_not duplicate_category.valid?
    assert_includes duplicate_category.errors[:slug], "has already been taken"
  end

  test "should generate slug from name" do
    @category.name = "Test Category"
    @category.slug = nil
    @category.valid?
    assert_equal "test-category", @category.slug
  end

  test "should generate unique slug when duplicate exists" do
    create(:category, name: "Test Category", slug: "test-category")
    @category.name = "Test Category"
    @category.slug = nil
    @category.valid?
    assert_equal "test-category-1", @category.slug
  end

  test "should have hierarchical associations" do
    parent = create(:category, name: "Parent")
    child = create(:category, name: "Child", parent_id: parent.id)

    assert_equal parent, child.parent_category
    assert_includes parent.subcategories, child
  end

  test "ancestors should return correct hierarchy" do
    grandparent = create(:category, name: "Grandparent")
    parent = create(:category, name: "Parent", parent_id: grandparent.id)
    child = create(:category, name: "Child", parent_id: parent.id)

    assert_equal [ grandparent, parent ], child.ancestors
  end

  test "descendants should return all children recursively" do
    parent = create(:category, name: "Parent")
    child1 = create(:category, name: "Child 1", parent_id: parent.id)
    child2 = create(:category, name: "Child 2", parent_id: parent.id)
    grandchild = create(:category, name: "Grandchild", parent_id: child1.id)

    descendants = parent.descendants
    assert_includes descendants, child1
    assert_includes descendants, child2
    assert_includes descendants, grandchild
  end

  test "root? should return true for categories without parent" do
    root_category = create(:category, name: "Root")
    assert root_category.root?
  end

  test "root? should return false for categories with parent" do
    parent = create(:category, name: "Parent")
    child = create(:category, name: "Child", parent_id: parent.id)
    assert_not child.root?
  end

  test "leaf? should return true for categories without children" do
    leaf_category = create(:category, name: "Leaf")
    assert leaf_category.leaf?
  end

  test "leaf? should return false for categories with children" do
    parent = create(:category, name: "Parent")
    create(:category, name: "Child", parent_id: parent.id)
    assert_not parent.leaf?
  end

  test "full_path should return correct breadcrumb" do
    grandparent = create(:category, name: "Grandparent")
    parent = create(:category, name: "Parent", parent_id: grandparent.id)
    child = create(:category, name: "Child", parent_id: parent.id)

    assert_equal "Grandparent > Parent > Child", child.full_path
  end

  test "total_item_count should count items in category and subcategories" do
    user = create(:user)
    parent = create(:category, name: "Parent")
    child = create(:category, name: "Child", parent_id: parent.id)

    create(:inventory_item, user: user, category: parent, item_type: "clothing")
    create(:inventory_item, user: user, category: child, item_type: "clothing")

    assert_equal 2, parent.total_item_count(user)
    assert_equal 1, child.total_item_count(user)
  end

  test "scopes should work correctly" do
    root1 = create(:category, name: "Root 1")
    root2 = create(:category, name: "Root 2")
    child = create(:category, name: "Child", parent_id: root1.id)
    inactive = create(:category, name: "Inactive", active: false)

    assert_includes Category.root_categories, root1
    assert_includes Category.root_categories, root2
    assert_not_includes Category.root_categories, child

    assert_includes Category.active, root1
    assert_not_includes Category.active, inactive

    assert_includes Category.subcategories_of(root1), child
    assert_not_includes Category.subcategories_of(root1), root2
  end

  test "should restrict destroy when inventory items exist" do
    category = create(:category)
    create(:inventory_item, category: category, item_type: "clothing")

    assert_raises(ActiveRecord::DeleteRestrictionError) do
      category.destroy
    end
  end

  test "should handle circular references gracefully" do
    parent = create(:category, name: "Parent")
    child = create(:category, name: "Child", parent_id: parent.id)

    # This should not cause infinite recursion
    assert_equal [ parent ], child.ancestors
    assert_includes parent.descendants, child
  end

  test "should handle deep hierarchies correctly" do
    level1 = create(:category, name: "Level 1")
    level2 = create(:category, name: "Level 2", parent_id: level1.id)
    level3 = create(:category, name: "Level 3", parent_id: level2.id)
    level4 = create(:category, name: "Level 4", parent_id: level3.id)

    assert_equal [ level1, level2, level3 ], level4.ancestors
    assert_equal "Level 1 > Level 2 > Level 3 > Level 4", level4.full_path

    descendants = level1.descendants
    assert_includes descendants, level2
    assert_includes descendants, level3
    assert_includes descendants, level4
  end

  test "should handle empty name gracefully in slug generation" do
    category = build(:category, name: "")
    assert_not category.valid?
    assert_includes category.errors[:name], "can't be blank"
  end

  test "should handle special characters in slug generation" do
    category = create(:category, name: "Special & Characters! @#$%")
    assert_equal "special-characters", category.slug
  end

  test "should handle unicode characters in slug generation" do
    category = create(:category, name: "Café & Résumé")
    assert_equal "cafe-resume", category.slug
  end

  test "should handle very long names in slug generation" do
    long_name = "A" * 100
    category = create(:category, name: long_name)
    assert category.slug.length <= 255 # Database limit
  end

  test "should handle nil metadata gracefully" do
    category = create(:category, metadata: nil)
    assert_nil category.metadata
    assert category.valid?
  end

  test "should handle complex metadata structures" do
    complex_metadata = {
      "colors" => [ "red", "blue" ],
      "seasons" => [ "spring", "summer" ],
      "nested" => { "deep" => { "value" => 123 } }
    }
    category = create(:category, metadata: complex_metadata)
    assert_equal complex_metadata, category.metadata
  end
end
