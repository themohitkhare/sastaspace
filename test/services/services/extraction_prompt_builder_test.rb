require "test_helper"

module Services
  class ExtractionPromptBuilderTest < ActiveSupport::TestCase
    def setup
      @user = create(:user, gender_preference: "men")
      @item_data = {
        "name" => "Grey Zip-Up Hoodie with Black Trim",
        "category_name" => "Hoodies",
        "category_matched" => "Hoodies",
        "colors" => [ "grey", "black" ],
        "material" => "cotton blend fleece",
        "style" => "athletic streetwear",
        "brand_matched" => "Gym King"
      }
      @builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: @user
      )
    end

    test "build_prompt includes item name" do
      prompt = @builder.build_prompt

      assert_includes prompt, "GREY ZIP-UP HOODIE WITH BLACK TRIM"
    end

    test "build_prompt includes gender context" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Gender Context: Men"
    end

    test "build_prompt uses unisex when gender_preference is nil" do
      user = create(:user, gender_preference: nil)
      builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Gender Context: Unisex"
    end

    test "build_prompt includes category information" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Category: Hoodies"
    end

    test "build_prompt includes subcategory when present" do
      item_data = @item_data.merge("subcategory" => "Zip-Up")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Category: Hoodies > Zip-Up"
    end

    test "build_prompt includes color specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Primary Color: grey"
      assert_includes prompt, "Secondary Colors: black"
    end

    test "build_prompt handles single color" do
      item_data = @item_data.merge("colors" => [ "blue" ])
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Primary Color: blue"
      assert_not_includes prompt, "Secondary Colors"
    end

    test "build_prompt handles empty colors array" do
      item_data = @item_data.merge("colors" => [])
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_not_includes prompt, "Primary Color"
    end

    test "build_prompt includes material specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Material: cotton blend fleece"
    end

    test "build_prompt handles missing material" do
      item_data = @item_data.except("material")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_not_includes prompt, "Material:"
    end

    test "build_prompt includes style/pattern specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Style/Pattern: athletic streetwear"
    end

    test "build_prompt uses style_notes when style is missing" do
      item_data = @item_data.except("style").merge("style_notes" => "casual wear")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Style/Pattern: casual wear"
    end

    test "build_prompt includes brand specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Brand: Gym King"
    end

    test "build_prompt uses brand_name when brand_matched is missing" do
      item_data = @item_data.except("brand_matched").merge("brand_name" => "Nike")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Brand: Nike"
    end

    test "build_prompt uses brand_suggestion when other brand fields are missing" do
      item_data = @item_data.except("brand_matched", "brand_name").merge("brand_suggestion" => "Adidas")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Brand: Adidas"
    end

    test "build_prompt includes all extraction requirements" do
      prompt = @builder.build_prompt

      assert_includes prompt, "REMOVE all background elements"
      assert_includes prompt, "REMOVE person/model"
      assert_includes prompt, "PRESERVE exact colors"
      assert_includes prompt, "PRESERVE all fabric texture"
      assert_includes prompt, "PRESERVE brand elements"
      assert_includes prompt, "MAINTAIN natural garment shape"
      assert_includes prompt, "SHOW all functional details"
    end

    test "build_prompt includes technical output specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Background: Pure white"
      assert_includes prompt, "Resolution: Minimum 800x800 pixels"
      assert_includes prompt, "Placement: Centered, front-facing"
      assert_includes prompt, "Lighting: Even, professional e-commerce style"
    end

    test "build_prompt includes DO NOT section" do
      prompt = @builder.build_prompt

      assert_includes prompt, "DO NOT:"
      assert_includes prompt, "Add artificial shadows"
      assert_includes prompt, "Alter colors from original"
      assert_includes prompt, "Remove functional garment details"
    end

    test "build_prompt handles missing name gracefully" do
      item_data = @item_data.except("name", "category_name")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "CLOTHING ITEM"
    end

    test "build_prompt handles women gender preference" do
      user = create(:user, gender_preference: "women")
      builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Gender Context: Women"
    end

    test "build_prompt handles unisex gender preference" do
      user = create(:user, gender_preference: "unisex")
      builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Gender Context: Unisex"
    end

    test "build_prompt uses category_matched over category_name" do
      item_data = @item_data.merge(
        "category_name" => "Hoodies",
        "category_matched" => "Sweatshirts"
      )
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Category: Sweatshirts"
      assert_not_includes prompt, "Category: Hoodies"
    end
  end
end
