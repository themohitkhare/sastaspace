require "test_helper"

class EmbeddingServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, :clothing)
    @brand = create(:brand, name: "Nike")
    @inventory_item = create(:inventory_item, :clothing,
                            user: @user,
                            category: @category,
                            brand: @brand,
                            name: "Blue T-Shirt",
                            metadata: { "color" => "blue", "material" => "cotton" })
  end

  test "generate_text_embedding returns nil for blank text" do
    assert_nil EmbeddingService.generate_text_embedding("")
    assert_nil EmbeddingService.generate_text_embedding(nil)
  end

  test "generate_text_embedding handles RubyLLM embedding call" do
    # Mock RubyLLM with Mocha - this is an external service
    mock_embedding = stub(vectors: Array.new(1024) { rand(-1.0..1.0) })
    RubyLLM.stubs(:embed).returns(mock_embedding)

    result = EmbeddingService.generate_text_embedding("test text")

    assert_not_nil result
    assert_equal 1024, result.length
  end

  test "generate_text_embedding falls back when embedding is nil" do
    RubyLLM.stubs(:embed).returns(nil)

    result = EmbeddingService.generate_text_embedding("test text")

    # Should return placeholder array
    assert_not_nil result
    assert_equal 1024, result.length
  end

  test "generate_text_embedding falls back on error" do
    RubyLLM.stubs(:embed).raises(StandardError, "Connection failed")

    result = EmbeddingService.generate_text_embedding("test text")

    # Should return placeholder array
    assert_not_nil result
    assert_equal 1024, result.length
  end

  test "build_item_description includes all relevant fields" do
    description = EmbeddingService.send(:build_item_description, @inventory_item)

    assert_includes description, "Blue T-Shirt"
    assert_includes description, "clothing"
    assert_includes description, "Nike"
  end
end
