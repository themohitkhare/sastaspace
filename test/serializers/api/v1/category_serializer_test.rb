require "test_helper"

class Api::V1::CategorySerializerTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @parent = create(:category, name: "Parent Category")
    @child = create(:category, name: "Child Category", parent_id: @parent.id)
    @grandchild = create(:category, name: "Grandchild Category", parent_id: @child.id)

    # Create some inventory items
    create(:inventory_item, user: @user, category: @parent, item_type: 'clothing')
    create(:inventory_item, user: @user, category: @child, item_type: 'clothing')
  end

  test "should serialize basic category attributes" do
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert_equal @parent.id, result[:id]
    assert_equal "Parent Category", result[:name]
    assert_equal "parent-category", result[:slug]
    assert_equal @parent.description, result[:description]
    assert_equal @parent.sort_order, result[:sort_order]
    assert_equal @parent.active, result[:active]
    assert_equal @parent.metadata, result[:metadata]
    assert_equal @parent.parent_id, result[:parent_id]
    assert_equal "Parent Category", result[:full_path]
    assert result[:is_root]
    assert_not result[:is_leaf]
    assert result[:created_at]
    assert result[:updated_at]
  end

  test "should include item count when requested" do
    serializer = Api::V1::CategorySerializer.new(@parent, { include_item_count: true, user: @user })
    result = serializer.as_json

    assert_equal 2, result[:item_count] # Parent + child items
  end

  test "should not include item count when not requested" do
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert_not result.key?(:item_count)
  end

  test "should return 0 item count when no user provided" do
    serializer = Api::V1::CategorySerializer.new(@parent, { include_item_count: true })
    result = serializer.as_json

    assert_equal 0, result[:item_count]
  end

  test "should include children when requested" do
    serializer = Api::V1::CategorySerializer.new(@parent, { include_children: true })
    result = serializer.as_json

    assert result.key?(:children)
    assert_equal 1, result[:children].length
    assert_equal "Child Category", result[:children].first[:name]
  end

  test "should not include children when not requested" do
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert_not result.key?(:children)
  end

  test "should recursively serialize children with same options" do
    serializer = Api::V1::CategorySerializer.new(@parent, {
      include_children: true,
      include_item_count: true,
      user: @user
    })
    result = serializer.as_json

    child = result[:children].first
    assert_equal 1, child[:item_count] # Only child's items
    assert child.key?(:children) # Should include grandchild
    assert_equal 1, child[:children].length
    assert_equal "Grandchild Category", child[:children].first[:name]
  end

  test "serialize_collection should serialize multiple categories" do
    categories = [ @parent, @child ]
    result = Api::V1::CategorySerializer.serialize_collection(categories, { include_item_count: true, user: @user })

    assert_equal 2, result.length
    assert_equal "Parent Category", result[0][:name]
    assert_equal "Child Category", result[1][:name]
    assert_equal 2, result[0][:item_count]
    assert_equal 1, result[1][:item_count]
  end

  test "serialize_tree should serialize categories with children" do
    categories = [ @parent ]
    result = Api::V1::CategorySerializer.serialize_tree(categories, { include_item_count: true, user: @user })

    assert_equal 1, result.length
    parent = result[0]
    assert_equal "Parent Category", parent[:name]
    assert parent.key?(:children)
    assert_equal 1, parent[:children].length
    assert_equal "Child Category", parent[:children].first[:name]
  end

  test "should handle leaf categories correctly" do
    serializer = Api::V1::CategorySerializer.new(@grandchild)
    result = serializer.as_json

    assert result[:is_leaf]
    assert_not result[:is_root]
    assert_equal "Parent Category > Child Category > Grandchild Category", result[:full_path]
  end

  test "should handle root categories correctly" do
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert result[:is_root]
    assert_not result[:is_leaf]
    assert_equal "Parent Category", result[:full_path]
  end

  test "should handle categories with metadata" do
    @parent.update!(metadata: { color: "blue", season: "summer" })
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert_equal({ "color" => "blue", "season" => "summer" }, result[:metadata])
  end

  test "should handle inactive categories" do
    @parent.update!(active: false)
    serializer = Api::V1::CategorySerializer.new(@parent)
    result = serializer.as_json

    assert_equal false, result[:active]
  end
end
