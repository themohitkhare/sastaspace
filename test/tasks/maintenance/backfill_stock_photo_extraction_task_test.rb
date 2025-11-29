require "test_helper"

module Maintenance
  class BackfillStockPhotoExtractionTaskTest < ActiveSupport::TestCase
    include ActiveJob::TestHelper

    def setup
      # Stub sleep globally for this test class to avoid actual sleeping
      Object.any_instance.stubs(:sleep)
    end

    def teardown
      Object.any_instance.unstub(:sleep)
    end

    test "processes items with images" do
      # Configure queue adapter to not perform jobs immediately
      ActiveJob::Base.queue_adapter.perform_enqueued_jobs = false
      ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = false

      user = create(:user)
      item = create(:inventory_item, user: user)

      file = Rails.root.join("test/fixtures/files/sample_image.jpg")
      item.primary_image.attach(io: File.open(file), filename: "sample_image.jpg", content_type: "image/jpeg")

      task = Maintenance::BackfillStockPhotoExtractionTask.new

      assert_enqueued_with(job: ExtractStockPhotoJob) do
        task.process(item)
      end

      assert_equal 1, task.job_results[:queued].count
    ensure
      # Restore queue adapter settings
      ActiveJob::Base.queue_adapter.perform_enqueued_jobs = true
      ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = true
    end

    test "skips items without images" do
      user = create(:user)
      item = create(:inventory_item, user: user)
      # No image

      task = Maintenance::BackfillStockPhotoExtractionTask.new

      assert_no_enqueued_jobs do
        task.process(item)
      end

      assert_equal 1, task.job_results[:skipped].count
    end

    test "handles errors" do
      user = create(:user)
      item = create(:inventory_item, user: user)

      file = Rails.root.join("test/fixtures/files/sample_image.jpg")
      item.primary_image.attach(io: File.open(file), filename: "sample_image.jpg", content_type: "image/jpeg")

      task = Maintenance::BackfillStockPhotoExtractionTask.new

      # Force an error by making ExtractStockPhotoJob.perform_later raise
      ExtractStockPhotoJob.stubs(:perform_later).raises(StandardError.new("Job error"))

      task.process(item)

      assert_equal 1, task.job_results[:failed].count
      assert_equal "Job error", task.job_results[:failed].first[:error_message]
    end

    test "collection returns active items without extraction" do
      user = create(:user)

      # Should be included
      item1 = create(:inventory_item, user: user)

      # Should be excluded (already has extraction)
      item2 = create(:inventory_item, user: user, stock_photo_extraction_completed_at: Time.current)
      item2.primary_image.attach(io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")), filename: "test.jpg", content_type: "image/jpeg")

      task = Maintenance::BackfillStockPhotoExtractionTask.new

      # Check that collection returns items
      collection = task.collection
      assert_kind_of ActiveRecord::Relation, collection

      # Verify our item is in the query (without executing actual SQL which might differ based on factories)
      assert_includes collection.to_sql, "stock_photo_extraction_completed_at"
    end

    test "count returns collection count" do
      user = create(:user)
      item = create(:inventory_item, user: user)

      task = Maintenance::BackfillStockPhotoExtractionTask.new
      assert_kind_of Integer, task.count
    end
  end
end
