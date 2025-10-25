require 'test_helper'

class AnalyzeClothingImageJobTest < ActiveJob::TestCase
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
                           material: 'cotton')
  end
  
  test "perform generates analysis and vector embedding" do
    # Mock the embedding generator
    mock_embedding = Array.new(1536) { rand(-1.0..1.0) }
    Ollama::EmbeddingGenerator.stub(:generate_item_embedding, mock_embedding) do
      # Mock the analysis methods
      job = AnalyzeClothingImageJob.new
      job.stub(:analyze_item, { 'item_type' => 'clothing', 'colors' => ['blue'], 'style' => 'casual', 'confidence' => 0.85 }) do
        job.stub(:extract_colors, ['blue']) do
          job.stub(:analyze_style, 'casual') do
            job.perform(@inventory_item.id)
          end
        end
      end
    end
    
    @inventory_item.reload
    
    # Check that vector was stored
    assert_not_nil @inventory_item.embedding_vector
    assert_equal 1536, @inventory_item.embedding_vector.length
    
    # Check that AI analysis was created
    analysis = @inventory_item.ai_analyses.last
    assert_not_nil analysis
    assert_equal 'visual_analysis', analysis.analysis_type
    assert_equal 0.85, analysis.confidence_score
    assert_equal 'clothing', analysis.analysis_data['item_type']
    assert_equal ['blue'], analysis.analysis_data['colors']
    assert_equal 'casual', analysis.analysis_data['style']
  end
  
  test "perform handles missing inventory item gracefully" do
    assert_raises(ActiveRecord::RecordNotFound) do
      AnalyzeClothingImageJob.perform_now(99999)
    end
  end
  
  test "perform handles embedding generation failure" do
    # Mock embedding generation failure
    Ollama::EmbeddingGenerator.stub(:generate_item_embedding, nil) do
      # Mock the analysis methods
      job = AnalyzeClothingImageJob.new
      job.stub(:analyze_item, { 'item_type' => 'clothing', 'colors' => ['blue'], 'style' => 'casual', 'confidence' => 0.85 }) do
        job.stub(:extract_colors, ['blue']) do
          job.stub(:analyze_style, 'casual') do
            job.perform(@inventory_item.id)
          end
        end
      end
    end
    
    @inventory_item.reload
    
    # Check that no vector was stored
    assert_nil @inventory_item.embedding_vector
    
    # Check that AI analysis was still created
    analysis = @inventory_item.ai_analyses.last
    assert_not_nil analysis
    assert_equal 'visual_analysis', analysis.analysis_type
  end
  
  test "perform handles analysis failure gracefully" do
    # Mock analysis failure
    job = AnalyzeClothingImageJob.new
    job.stub(:analyze_item, -> { raise StandardError.new("Analysis failed") }) do
      assert_raises(StandardError) do
        job.perform(@inventory_item.id)
      end
    end
    
    @inventory_item.reload
    
    # Check that no analysis was created
    assert_equal 0, @inventory_item.ai_analyses.count
  end
  
  test "extract_colors returns item color" do
    job = AnalyzeClothingImageJob.new
    colors = job.send(:extract_colors, @inventory_item)
    
    assert_equal ['blue'], colors
  end
  
  test "extract_colors handles missing color" do
    @inventory_item.update!(color: nil)
    
    job = AnalyzeClothingImageJob.new
    colors = job.send(:extract_colors, @inventory_item)
    
    assert_equal [], colors
  end
  
  test "analyze_style returns occasion or defaults to casual" do
    job = AnalyzeClothingImageJob.new
    style = job.send(:analyze_style, @inventory_item)
    
    assert_equal 'casual', style
  end
  
  test "analyze_style uses occasion from metadata" do
    @inventory_item.update!(occasion: 'formal')
    
    job = AnalyzeClothingImageJob.new
    style = job.send(:analyze_style, @inventory_item)
    
    assert_equal 'formal', style
  end
  
  test "analyze_item returns comprehensive analysis" do
    job = AnalyzeClothingImageJob.new
    analysis = job.send(:analyze_item, @inventory_item)
    
    assert_equal 'clothing', analysis['item_type']
    assert_equal ['blue'], analysis['colors']
    assert_equal 'casual', analysis['style']
    assert_equal 0.85, analysis['confidence']
  end
end
