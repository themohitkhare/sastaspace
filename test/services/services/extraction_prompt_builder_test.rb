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

      assert_includes prompt, "Gender: Men"
    end

    test "build_prompt uses unisex when gender_preference is nil" do
      user = create(:user, gender_preference: nil)
      builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Gender: Unisex"
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

      assert_includes prompt, "Remove ALL human elements"
      assert_includes prompt, "PRESERVE exact colors"
      assert_includes prompt, "show fabric texture clearly"
      assert_includes prompt, "keep logo visible if present"
      assert_includes prompt, "Maintain natural proportions"
      assert_includes prompt, "Show complete sweater shape"
    end

    test "build_prompt includes technical output specifications" do
      prompt = @builder.build_prompt

      assert_includes prompt, "Pure solid white background"
      assert_includes prompt, "High-resolution, sharp focus"
      assert_includes prompt, "Centered, professional product photography"
      assert_includes prompt, "Professional e-commerce studio lighting"
    end

    test "build_prompt includes DO NOT section" do
      prompt = @builder.build_prompt

      assert_includes prompt, "NEGATIVE PROMPT (STRICTLY AVOID):"
      assert_includes prompt, "human, person, model"
      assert_includes prompt, "colored background"
      assert_includes prompt, "casual styling"
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

      assert_includes prompt, "Gender: Women"
    end

    test "build_prompt handles unisex gender preference" do
      user = create(:user, gender_preference: "unisex")
      builder = ExtractionPromptBuilder.new(
        item_data: @item_data,
        user: user
      )

      prompt = builder.build_prompt

      assert_includes prompt, "Gender: Unisex"
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

    test "description_section returns default when description is missing" do
      item_data = @item_data.except("description")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "No description provided"
    end

    test "build_prompt handles dress category presentation" do
      item_data = @item_data.merge("category_matched" => "Dress")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "For dresses"
      assert_includes prompt, "full silhouette"
    end

    test "build_prompt handles shoe category presentation" do
      item_data = @item_data.merge("category_matched" => "Sneakers")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "For footwear"
      assert_includes prompt, "side view and front view"
    end

    test "build_prompt handles accessory category presentation" do
      item_data = @item_data.merge("category_matched" => "Accessories")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "For accessories"
    end

    test "build_prompt handles description with pockets" do
      item_data = @item_data.merge("description" => "Jacket with side pockets")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "pockets are clearly visible"
    end

    test "build_prompt handles description with zipper" do
      item_data = @item_data.merge("description" => "Hoodie with front zipper")
      builder = ExtractionPromptBuilder.new(
        item_data: item_data,
        user: @user
      )

      prompt = builder.build_prompt
      assert_includes prompt, "zipper details clearly"
    end
  end
end
