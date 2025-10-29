require "test_helper"

class AnalyzeClothingImageJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  test "queues and performs analysis via analyzer factory" do
    mock_analyzer = mock()
    mock_analyzer.expects(:analyze).once
    Services::AnalyzerFactory.stubs(:create_analyzer).returns(mock_analyzer)

    assert_enqueued_with(job: AnalyzeClothingImageJob, args: [ @item.id ]) do
      AnalyzeClothingImageJob.perform_later(@item.id)
    end

    assert_nothing_raised do
      AnalyzeClothingImageJob.perform_now(@item.id)
    end
  end

  test "logs and re-raises on error" do
    Services::AnalyzerFactory.stubs(:create_analyzer).raises(StandardError, "boom")

    assert_raises(StandardError) do
      AnalyzeClothingImageJob.perform_now(@item.id)
    end
  end
end
