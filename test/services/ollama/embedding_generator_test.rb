require 'test_helper'

class Ollama::EmbeddingGeneratorTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, name: 'tops')
    @brand = create(:brand, name: 'Nike')
    @inventory_item = create(:inventory_item, 
                           user: @user, 
                           category: @category, 
                           brand: @brand,
                           name: 'Blue T-Shirt',
                           color: 'blue',
                           material: 'cotton',
                           season: 'summer',
                           occasion: 'casual')
  end
  
  test "generate_text_embedding returns embedding for valid text" do
    text = "blue casual cotton shirt"
    
    # Mock the Ollama API response
    mock_response = {
      'embedding' => Array.new(1536) { rand(-1.0..1.0) }
    }
    
    Ollama::EmbeddingGenerator.stub(:generate_embedding, mock_response) do
      result = Ollama::EmbeddingGenerator.generate_text_embedding(text)
      
      assert_not_nil result
      assert_equal 1536, result.length
      assert result.all? { |val| val.is_a?(Numeric) }
    end
  end
  
  test "generate_text_embedding returns nil for blank text" do
    result = Ollama::EmbeddingGenerator.generate_text_embedding("")
    assert_nil result
    
    result = Ollama::EmbeddingGenerator.generate_text_embedding(nil)
    assert_nil result
  end
  
  test "generate_text_embedding handles API errors gracefully" do
    text = "blue casual cotton shirt"
    
    # Mock API error
    Ollama::EmbeddingGenerator.stub(:generate_embedding, -> { raise StandardError.new("API Error") }) do
      result = Ollama::EmbeddingGenerator.generate_text_embedding(text)
      assert_nil result
    end
  end
  
  test "generate_image_embedding returns embedding for valid image" do
    image_path = Rails.root.join('test', 'fixtures', 'files', 'test_image.jpg')
    
    # Mock the Ollama API response
    mock_response = {
      'embedding' => Array.new(1536) { rand(-1.0..1.0) }
    }
    
    Ollama::EmbeddingGenerator.stub(:generate_image_embedding_from_path, mock_response) do
      result = Ollama::EmbeddingGenerator.generate_image_embedding(image_path)
      
      assert_not_nil result
      assert_equal 1536, result.length
      assert result.all? { |val| val.is_a?(Numeric) }
    end
  end
  
  test "generate_image_embedding returns nil for non-existent file" do
    image_path = '/non/existent/path.jpg'
    
    result = Ollama::EmbeddingGenerator.generate_image_embedding(image_path)
    assert_nil result
  end
  
  test "generate_item_embedding creates comprehensive description" do
    # Mock the text embedding generation
    mock_embedding = Array.new(1536) { rand(-1.0..1.0) }
    
    Ollama::EmbeddingGenerator.stub(:generate_text_embedding, mock_embedding) do
      result = Ollama::EmbeddingGenerator.generate_item_embedding(@inventory_item)
      
      assert_not_nil result
      assert_equal 1536, result.length
    end
  end
  
  test "build_item_description includes all relevant fields" do
    description = Ollama::EmbeddingGenerator.send(:build_item_description, @inventory_item)
    
    assert_includes description, 'Blue T-Shirt'
    assert_includes description, 'tops'
    assert_includes description, 'Nike'
    assert_includes description, 'blue'
    assert_includes description, 'cotton'
    assert_includes description, 'summer'
    assert_includes description, 'casual'
  end
  
  test "build_item_description handles missing optional fields" do
    @inventory_item.update!(brand: nil, color: nil, material: nil)
    
    description = Ollama::EmbeddingGenerator.send(:build_item_description, @inventory_item)
    
    assert_includes description, 'Blue T-Shirt'
    assert_includes description, 'tops'
    assert_not_includes description, 'Nike'
    assert_not_includes description, 'blue'
    assert_not_includes description, 'cotton'
  end
end
