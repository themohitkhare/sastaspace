require "test_helper"

class InventoryItemImageProcessingCallbacksTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper
  test "enqueue image processing job after attaching primary image" do
    ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = true
    ActiveJob::Base.queue_adapter.perform_enqueued_jobs = false

    item = create(:inventory_item)

    assert_enqueued_with(job: ImageProcessingJob) do
      item.primary_image.attach(
        io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
        filename: "sample.jpg",
        content_type: "image/jpeg"
      )
      item.save!
    end
  end

  test "enqueue image processing job for each additional image on update" do
    ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = true
    ActiveJob::Base.queue_adapter.perform_enqueued_jobs = false

    item = create(:inventory_item)
    file_path = Rails.root.join("test", "fixtures", "files", "sample_image.jpg")

    2.times do |i|
      assert_enqueued_with(job: ImageProcessingJob) do
        item.additional_images.attach(
          io: File.open(file_path),
          filename: "extra-#{i}.jpg",
          content_type: "image/jpeg"
        )
        item.save!
      end
    end
  end
end


