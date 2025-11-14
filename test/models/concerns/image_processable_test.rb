require "test_helper"
require "action_dispatch/http/upload"
require "tempfile"

class ImageProcessableTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @category = create(:category)
    @item = create(:inventory_item, user: @user, category: @category)
  end

  test "primary_image_variants returns variants when image attached" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    tempfile = Tempfile.new([ "test", ".jpg" ])
    tempfile.write("fake image data")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.jpg",
      type: "image/jpeg"
    )

    @item.primary_image.attach(
      io: file.open,
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    variants = @item.primary_image_variants
    assert variants.is_a?(Hash)
    assert variants.key?(:thumb)
    assert variants.key?(:medium)
    assert variants.key?(:large)
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "primary_image_variants returns empty hash when no image" do
    variants = @item.primary_image_variants
    assert_equal Hash.new, variants
  end

  test "additional_image_variants returns variants when image provided" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    tempfile = Tempfile.new([ "test", ".jpg" ])
    tempfile.write("fake image data")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.jpg",
      type: "image/jpeg"
    )

    @item.additional_images.attach(
      io: file.open,
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    image = @item.additional_images.first
    variants = @item.additional_image_variants(image)
    assert variants.is_a?(Hash)
    assert variants.key?(:thumb)
    assert variants.key?(:medium)
    assert variants.key?(:large)
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "additional_image_variants returns empty hash when nil" do
    variants = @item.additional_image_variants(nil)
    assert_equal Hash.new, variants
  end

  test "additional_image_variants returns empty hash when not attached" do
    # Create a mock object that responds to attached? but returns false
    mock_image = Object.new
    def mock_image.attached?
      false
    end

    variants = @item.additional_image_variants(mock_image)
    assert_equal Hash.new, variants
  end

  test "validates primary image content type" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    tempfile = Tempfile.new([ "test", ".txt" ])
    tempfile.write("not an image")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.txt",
      type: "text/plain"
    )

    @item.primary_image.attach(
      io: file.open,
      filename: "test.txt",
      content_type: "text/plain"
    )

    assert_not @item.valid?
    assert @item.errors[:primary_image].any?
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "validates primary image size" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    # Create a large file (simulated)
    large_data = "x" * (6.megabytes)
    tempfile = Tempfile.new([ "large", ".jpg" ])
    tempfile.write(large_data)
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "large.jpg",
      type: "image/jpeg"
    )

    # Attach the large file
    @item.primary_image.attach(
      io: file.open,
      filename: "large.jpg",
      content_type: "image/jpeg"
    )

    # Validation should catch the size issue
    assert_not @item.valid?
    assert @item.errors[:primary_image].any?
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "process_images handles additional images" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    tempfile1 = Tempfile.new([ "test1", ".jpg" ])
    tempfile1.write("fake image data 1")
    tempfile1.rewind

    tempfile2 = Tempfile.new([ "test2", ".jpg" ])
    tempfile2.write("fake image data 2")
    tempfile2.rewind

    file1 = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile1,
      filename: "test1.jpg",
      type: "image/jpeg"
    )

    file2 = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile2,
      filename: "test2.jpg",
      type: "image/jpeg"
    )

    @item.additional_images.attach(
      [ { io: file1.open, filename: "test1.jpg", content_type: "image/jpeg" },
        { io: file2.open, filename: "test2.jpg", content_type: "image/jpeg" } ]
    )

    # Verify additional images are attached
    assert_equal 2, @item.additional_images.count
  ensure
    tempfile1&.close
    tempfile1&.unlink
    tempfile2&.close
    tempfile2&.unlink
  end

  test "validates additional images content type" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    tempfile = Tempfile.new([ "test", ".txt" ])
    tempfile.write("not an image")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.txt",
      type: "text/plain"
    )

    @item.additional_images.attach(
      io: file.open,
      filename: "test.txt",
      content_type: "text/plain"
    )

    assert_not @item.valid?
    assert @item.errors[:additional_images].any?
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "validates additional images size" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    large_data = "x" * (6.megabytes)
    tempfile = Tempfile.new([ "large", ".jpg" ])
    tempfile.write(large_data)
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "large.jpg",
      type: "image/jpeg"
    )

    @item.additional_images.attach(
      io: file.open,
      filename: "large.jpg",
      content_type: "image/jpeg"
    )

    assert_not @item.valid?
    assert @item.errors[:additional_images].any?
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "process_images handles item without primary image" do
    # Item with no images should not call job
    item = create(:inventory_item, user: @user, category: @category)
    ImageProcessingJob.expects(:perform_later).never
    item.save!
  end

  test "process_images handles item with only additional images" do
    tempfile = Tempfile.new([ "test", ".jpg" ])
    tempfile.write("fake image data")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.jpg",
      type: "image/jpeg"
    )

    @item.additional_images.attach(
      io: file.open,
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    # Should process additional images
    ImageProcessingJob.expects(:perform_later).at_least_once
    @item.save!
  ensure
    tempfile&.close
    tempfile&.unlink
  end
end
