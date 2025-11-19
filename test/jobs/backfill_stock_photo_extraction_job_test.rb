require "test_helper"

class BackfillStockPhotoExtractionJobTest < ActiveJob::TestCase
  test "performs backfill for specified items" do
    user = create(:user)
    item1 = create(:inventory_item, user: user)
    item2 = create(:inventory_item, user: user)

    # Attach images
    file = Rails.root.join("test/fixtures/files/test_image.jpg")
    item1.primary_image.attach(io: File.open(file), filename: "test_image.jpg", content_type: "image/jpeg")
    item2.primary_image.attach(io: File.open(file), filename: "test_image.jpg", content_type: "image/jpeg")

    # Mock the service
    service_mock = mock
    service_mock.expects(:queue_extraction).twice

    StockPhotoExtractionService.expects(:new).twice.returns(service_mock)

    BackfillStockPhotoExtractionJob.perform_now(user.id, [ item1.id, item2.id ])
  end

  test "skips items without images" do
    user = create(:user)
    item = create(:inventory_item, user: user)
    # No image attached

    StockPhotoExtractionService.expects(:new).never

    BackfillStockPhotoExtractionJob.perform_now(user.id, [ item.id ])
  end

  test "handles errors gracefully" do
    user = create(:user)
    item = create(:inventory_item, user: user)

    file = Rails.root.join("test/fixtures/files/test_image.jpg")
    item.primary_image.attach(io: File.open(file), filename: "test_image.jpg", content_type: "image/jpeg")

    StockPhotoExtractionService.expects(:new).raises(StandardError.new("Service error"))

    assert_nothing_raised do
      result = BackfillStockPhotoExtractionJob.perform_now(user.id, [ item.id ])
      assert_equal 1, result[:errors].count
      assert_equal "Service error", result[:errors].first[:error]
    end
  end
end
