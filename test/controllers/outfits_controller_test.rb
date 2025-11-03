require "test_helper"

class OutfitsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    OutfitsController.any_instance.stubs(:authenticate_user!).returns(true)
    OutfitsController.any_instance.stubs(:current_user).returns(@user)
  end

  test "index renders successfully" do
    get outfits_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "new renders successfully" do
    get new_outfit_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "create creates outfit and redirects" do
    assert_difference -> { @user.outfits.count }, +1 do
      post outfits_path, params: { outfit: { name: "Casual", description: "Weekend", occasion: "casual" } }, headers: { "Accept" => "text/html" }
    end
    outfit = @user.outfits.last
    assert_redirected_to outfit_path(outfit)
  end

  test "create renders errors on failure" do
    post outfits_path, params: { outfit: { name: nil } }, headers: { "Accept" => "text/html" }
    assert_response :unprocessable_entity
  end

  test "show renders successfully" do
    outfit = @user.outfits.create!(name: "Look", description: "desc", occasion: "work")
    get outfit_path(outfit), headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "edit renders successfully" do
    outfit = @user.outfits.create!(name: "Look", description: "desc", occasion: "work")
    get edit_outfit_path(outfit), headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "builder renders successfully" do
    get builder_outfits_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "inspiration renders successfully" do
    get inspiration_outfits_path, headers: { "Accept" => "text/html" }
    assert_response :success
  end

  test "index filters by occasion" do
    casual = @user.outfits.create!(name: "Casual Look", occasion: "casual")
    formal = @user.outfits.create!(name: "Formal Look", occasion: "formal")

    get outfits_path, params: { occasion: "casual" }, headers: { "Accept" => "text/html" }
    assert_response :success
    assert_match(/Casual Look/, @response.body)
    assert_no_match(/Formal Look/, @response.body)
  end

  test "index filters by favorites" do
    favorite = @user.outfits.create!(name: "Favorite Outfit", is_favorite: true)
    normal = @user.outfits.create!(name: "Normal Outfit", is_favorite: false)

    get outfits_path, params: { favorite: "true" }, headers: { "Accept" => "text/html" }
    assert_response :success
    assert_match(/Favorite Outfit/, @response.body)
    assert_no_match(/Normal Outfit/, @response.body)
  end

  test "index filters by date_range today" do
    old_outfit = @user.outfits.create!(name: "Old Outfit", created_at: 2.days.ago)
    new_outfit = @user.outfits.create!(name: "New Outfit", created_at: 1.hour.ago)

    get outfits_path, params: { date_range: "today" }, headers: { "Accept" => "text/html" }
    assert_response :success
    assert_match(/New Outfit/, @response.body)
    assert_no_match(/Old Outfit/, @response.body)
  end

  test "index searches by name" do
    weekend = @user.outfits.create!(name: "Weekend Look", description: "Casual outfit")
    office = @user.outfits.create!(name: "Office Attire", description: "Formal")

    get outfits_path, params: { search: "Weekend" }, headers: { "Accept" => "text/html" }
    assert_response :success
    assert_match(/Weekend Look/, @response.body)
    assert_no_match(/Office Attire/, @response.body)
  end

  test "index searches by description" do
    weekend = @user.outfits.create!(name: "Weekend Look", description: "Casual outfit")
    office = @user.outfits.create!(name: "Office Attire", description: "Formal wear")

    get outfits_path, params: { search: "Casual" }, headers: { "Accept" => "text/html" }
    assert_response :success
    assert_match(/Weekend Look/, @response.body)
  end

  test "index sorts by name ascending" do
    zebra = @user.outfits.create!(name: "Zebra Outfit")
    apple = @user.outfits.create!(name: "Apple Outfit")

    get outfits_path, params: { sort: "name_asc" }, headers: { "Accept" => "text/html" }
    assert_response :success
    body = @response.body
    apple_index = body.index("Apple Outfit")
    zebra_index = body.index("Zebra Outfit")
    assert apple_index < zebra_index, "Apple should come before Zebra"
  end

  test "index sorts by name descending" do
    apple = @user.outfits.create!(name: "Apple Outfit")
    zebra = @user.outfits.create!(name: "Zebra Outfit")

    get outfits_path, params: { sort: "name_desc" }, headers: { "Accept" => "text/html" }
    assert_response :success
    body = @response.body
    zebra_index = body.index("Zebra Outfit")
    apple_index = body.index("Apple Outfit")
    assert zebra_index < apple_index, "Zebra should come before Apple"
  end

  test "create creates outfit with inventory_item_ids" do
    category = create(:category, name: "Test Category #{SecureRandom.hex(4)}")
    item1 = create(:inventory_item, user: @user, category: category, name: "Item 1")
    item2 = create(:inventory_item, user: @user, category: category, name: "Item 2")

    assert_difference -> { @user.outfits.count }, +1 do
      post outfits_path, params: {
        outfit: {
          name: "My Outfit",
          description: "Test outfit",
          inventory_item_ids: [ item1.id, item2.id ]
        }
      }, headers: { "Accept" => "text/html" }
    end

    outfit = @user.outfits.last
    assert_equal 2, outfit.inventory_items.count
    assert_includes outfit.inventory_items, item1
    assert_includes outfit.inventory_items, item2
    assert_redirected_to outfit_path(outfit)
  end

  test "create handles invalid inventory_item_ids gracefully" do
    category = create(:category, name: "Test Category #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category)

    assert_difference -> { @user.outfits.count }, +1 do
      post outfits_path, params: {
        outfit: {
          name: "My Outfit",
          inventory_item_ids: [ item.id, 99999 ] # One invalid ID
        }
      }, headers: { "Accept" => "text/html" }
    end

    outfit = @user.outfits.last
    # Should only include the valid item
    assert_equal 1, outfit.inventory_items.count
    assert_includes outfit.inventory_items, item
  end

  test "update updates outfit attributes and inventory_item_ids" do
    category = create(:category, name: "Cat #{SecureRandom.hex(4)}")
    item1 = create(:inventory_item, user: @user, category: category, name: "One")
    item2 = create(:inventory_item, user: @user, category: category, name: "Two")
    outfit = @user.outfits.create!(name: "Orig", description: "desc", occasion: "casual")
    outfit.outfit_items.create!(inventory_item: item1)

    patch outfit_path(outfit), params: {
      outfit: {
        name: "Updated Name",
        description: "New desc",
        occasion: "formal",
        inventory_item_ids: [ item1.id, item2.id ]
      }
    }, headers: { "Accept" => "text/html" }

    assert_redirected_to outfit_path(outfit)
    outfit.reload
    assert_equal "Updated Name", outfit.name
    assert_equal "formal", outfit.occasion
    assert_equal 2, outfit.inventory_items.count
    assert_includes outfit.inventory_items, item1
    assert_includes outfit.inventory_items, item2
  end

  test "update clears outfit_items when no inventory_item_ids provided" do
    category = create(:category, name: "Cat #{SecureRandom.hex(4)}")
    item1 = create(:inventory_item, user: @user, category: category, name: "One")
    outfit = @user.outfits.create!(name: "Orig2", description: "desc", occasion: "casual")
    outfit.outfit_items.create!(inventory_item: item1)

    patch outfit_path(outfit), params: {
      outfit: {
        name: "Still Name",
        description: "Still desc"
        # no inventory_item_ids
      }
    }, headers: { "Accept" => "text/html" }

    assert_redirected_to outfit_path(outfit)
    outfit.reload
    assert_equal 0, outfit.outfit_items.count
  end

  test "index displays available_occasions for filter dropdown" do
    @user.outfits.create!(name: "Casual", occasion: "casual")
    @user.outfits.create!(name: "Formal", occasion: "formal")

    get outfits_path, headers: { "Accept" => "text/html" }
    assert_response :success
    # Should render filter form with occasion options
    assert_match(/occasion/i, @response.body)
  end

  test "destroy deletes outfit and redirects" do
    outfit = @user.outfits.create!(name: "To Delete", description: "desc", occasion: "casual")
    assert_difference -> { @user.outfits.count }, -1 do
      delete outfit_path(outfit), headers: { "Accept" => "text/html" }
    end
    assert_redirected_to outfits_path
  end

  test "destroy deletes associated outfit_items" do
    category = create(:category, name: "Cat #{SecureRandom.hex(4)}")
    item = create(:inventory_item, user: @user, category: category, name: "Item")
    outfit = @user.outfits.create!(name: "To Delete", description: "desc")
    outfit.outfit_items.create!(inventory_item: item)

    assert_difference -> { OutfitItem.count }, -1 do
      delete outfit_path(outfit), headers: { "Accept" => "text/html" }
    end
    assert_redirected_to outfits_path
  end
end
