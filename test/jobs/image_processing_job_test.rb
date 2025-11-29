require "test_helper"

class ImageProcessingJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @category = create(:category, :clothing)
    @inventory_item = create(:inventory_item, :clothing, user: @user, category: @category)
  end

  teardown do
    # Clean up all stubs to prevent interference with other tests
    Rails.logger.unstub_all if Rails.logger.respond_to?(:unstub_all)
    ImageProcessingJob.unstub_all if ImageProcessingJob.respond_to?(:unstub_all)
    # Clean up any_instance stubs
    ImageProcessingJob.any_instance.unstub_all if ImageProcessingJob.any_instance.respond_to?(:unstub_all)
  end

  test "should process primary image variants" do
    # Attach a test image
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    # Configure queue adapter to not perform jobs immediately
    ActiveJob::Base.queue_adapter.perform_enqueued_jobs = false
    ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = false

    assert_enqueued_with(job: ImageProcessingJob) do
      ImageProcessingJob.perform_later(@inventory_item)
    end
  ensure
    # Restore queue adapter settings
    ActiveJob::Base.queue_adapter.perform_enqueued_jobs = true
    ActiveJob::Base.queue_adapter.perform_enqueued_at_jobs = true
  end

  test "should process additional image variants" do
    # Attach additional images
    @inventory_item.additional_images.attach([
      {
        io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
        filename: "test1.jpg",
        content_type: "image/jpeg"
      },
      {
        io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
        filename: "test2.jpg",
        content_type: "image/jpeg"
      }
    ])

    additional_image = @inventory_item.additional_images.first

    assert_nothing_raised do
      ImageProcessingJob.perform_now(@inventory_item, additional_image.id)
    end
  end

  test "should handle missing image gracefully" do
    Rails.logger.stubs(:error)
    assert_nothing_raised do
      ImageProcessingJob.perform_now(@inventory_item, 99999)
    end
  end

  test "process_image_variants handles nil image" do
    job = ImageProcessingJob.new
    assert_nothing_raised do
      job.send(:process_image_variants, nil)
    end
  end

  test "process_image_variants handles unattached image" do
    job = ImageProcessingJob.new
    unattached_image = mock
    unattached_image.stubs(:respond_to?).with(:attached?).returns(true)
    unattached_image.stubs(:attached?).returns(false)

    assert_nothing_raised do
      job.send(:process_image_variants, unattached_image)
    end
  end

  test "process_image_variants generates variants for attached image" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image

    # Stub variant calls to avoid actual processing
    image.stubs(:variant).returns(mock)
    Rails.logger.stubs(:info)

    assert_nothing_raised do
      job.send(:process_image_variants, image)
    end
  end

  test "process_image_variants logs success message" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:variant).returns(mock)
    image.stubs(:id).returns(123)

    log_messages = []
    Rails.logger.stubs(:info).with { |msg| log_messages << msg; true }

    job.send(:process_image_variants, image)

    log_message = log_messages.find { |msg| msg.include?("Generated variants") }
    assert log_message.present?, "Should log variant generation"
  end

  test "strip_exif_data handles nil image" do
    job = ImageProcessingJob.new
    assert_nothing_raised do
      job.send(:strip_exif_data, nil)
    end
  end

  test "strip_exif_data handles unattached image" do
    job = ImageProcessingJob.new
    unattached_image = mock
    unattached_image.stubs(:respond_to?).with(:attached?).returns(true)
    unattached_image.stubs(:attached?).returns(false)

    assert_nothing_raised do
      job.send(:strip_exif_data, unattached_image)
    end
  end

  test "strip_exif_data handles errors gracefully" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:id).returns(123)

    # Stub variant to raise error
    mock_variant = mock
    mock_variant.stubs(:processed).raises(StandardError.new("Processing error"))
    image.stubs(:variant).returns(mock_variant)

    Rails.logger.stubs(:warn)

    # Should not raise, just log warning
    assert_nothing_raised do
      job.send(:strip_exif_data, image)
    end
  end

  test "strip_exif_data logs success message" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:id).returns(123)

    mock_variant = mock
    mock_variant.stubs(:processed).returns(true)
    image.stubs(:variant).returns(mock_variant)

    log_messages = []
    Rails.logger.stubs(:info).with { |msg| log_messages << msg; true }

    job.send(:strip_exif_data, image)

    log_message = log_messages.find { |msg| msg.include?("Stripped EXIF data") }
    assert log_message.present?, "Should log EXIF stripping"
  end

  test "strip_exif_data logs warning on error" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:id).returns(123)

    mock_variant = mock
    mock_variant.stubs(:processed).raises(StandardError.new("Error"))
    image.stubs(:variant).returns(mock_variant)

    log_messages = []
    Rails.logger.stubs(:warn).with { |msg| log_messages << msg; true }

    job.send(:strip_exif_data, image)

    log_message = log_messages.find { |msg| msg.include?("Failed to strip EXIF") }
    assert log_message.present?, "Should log warning on error"
  end

  test "strip_exif_data handles Vips errors gracefully" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:id).returns(192)

    # Define Vips::Error if not already defined (for testing)
    unless defined?(Vips::Error)
      module Vips
        class Error < StandardError; end
      end
    end

    # Simulate Vips error (like "Bogus marker length")
    mock_variant = mock
    mock_variant.stubs(:processed).raises(Vips::Error.new("VipsJpeg: Bogus marker length"))
    image.stubs(:variant).returns(mock_variant)

    log_messages = []
    Rails.logger.stubs(:warn).with { |msg| log_messages << msg; true }
    Rails.logger.stubs(:debug).with { |msg| log_messages << msg; true }

    # Should not raise, just log warning
    assert_nothing_raised do
      job.send(:strip_exif_data, image)
    end

    log_message = log_messages.find { |msg| msg.include?("Vips error") }
    assert log_message.present?, "Should log Vips error warning"
  end

  test "process_image_variants handles Vips errors gracefully" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    image = @inventory_item.primary_image
    image.stubs(:id).returns(192)

    # Define Vips::Error if not already defined (for testing)
    unless defined?(Vips::Error)
      module Vips
        class Error < StandardError; end
      end
    end

    # Simulate Vips error during variant generation
    image.stubs(:variant).raises(Vips::Error.new("VipsJpeg: Bogus marker length"))

    log_messages = []
    Rails.logger.stubs(:warn).with { |msg| log_messages << msg; true }
    Rails.logger.stubs(:debug).with { |msg| log_messages << msg; true }

    # Should not raise, just log warning
    assert_nothing_raised do
      job.send(:process_image_variants, image)
    end

    log_message = log_messages.find { |msg| msg.include?("Vips error") }
    assert log_message.present?, "Should log Vips error warning"
  end

  test "perform handles StandardError and re-raises" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    # Stub process_image_variants to raise error
    ImageProcessingJob.any_instance.stubs(:process_image_variants).raises(StandardError.new("Processing error"))
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      ImageProcessingJob.perform_now(@inventory_item)
    end
  end

  test "perform processes primary image when additional_image_id is nil" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    job = ImageProcessingJob.new
    job.stubs(:process_image_variants)
    job.stubs(:strip_exif_data)

    job.expects(:process_image_variants).with(@inventory_item.primary_image)
    job.expects(:strip_exif_data).with(@inventory_item.primary_image)

    job.perform(@inventory_item, nil)
  end

  test "perform processes additional image when additional_image_id is provided" do
    @inventory_item.additional_images.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    additional_image = @inventory_item.additional_images.first

    job = ImageProcessingJob.new
    job.stubs(:process_image_variants)
    job.stubs(:strip_exif_data)

    job.expects(:process_image_variants).with(additional_image)
    job.expects(:strip_exif_data).with(additional_image)

    job.perform(@inventory_item, additional_image.id)
  end

  test "perform logs error for RecordNotFound" do
    log_messages = []
    Rails.logger.stubs(:error).with { |msg| log_messages << msg; true }

    ImageProcessingJob.perform_now(@inventory_item, 99999)

    error_log = log_messages.find { |msg| msg.include?("Image not found") }
    assert error_log.present?, "Should log error for RecordNotFound"
  end

  test "perform logs error for StandardError" do
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join("test", "fixtures", "files", "sample_image.jpg")),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    ImageProcessingJob.any_instance.stubs(:process_image_variants).raises(StandardError.new("Test error"))
    log_messages = []
    Rails.logger.stubs(:error).with { |msg| log_messages << msg; true }

    assert_raises(StandardError) do
      ImageProcessingJob.perform_now(@inventory_item)
    end

    error_log = log_messages.find { |msg| msg.include?("Error processing image") }
    assert error_log.present?, "Should log error for StandardError"
  end
end
