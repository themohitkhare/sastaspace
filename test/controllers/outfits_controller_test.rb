require "test_helper"

class OutfitsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = create(:user)
    OutfitsController.any_instance.stubs(:require_login).returns(true)
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
end
