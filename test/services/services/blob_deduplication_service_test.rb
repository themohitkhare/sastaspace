require "test_helper"

class Services::BlobDeduplicationServiceTest < ActiveSupport::TestCase
  setup do
    # Use test storage for ActiveStorage
    # Note: ActiveStorage uses :test service in test environment
    @io1 = File.open(Rails.root.join("test/fixtures/files/sample_image.jpg"))
    @io2 = File.open(Rails.root.join("test/fixtures/files/sample_image.jpg"))
    @io3 = StringIO.new("different content")
  end

  teardown do
    @io1&.close
    @io2&.close
    @io3&.close
  end

  test "find_or_create_blob creates new blob for first upload" do
    blob = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io1,
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    assert blob.persisted?
    assert_equal "test.jpg", blob.filename.to_s
    assert_equal "image/jpeg", blob.content_type
  end

  test "find_or_create_blob reuses existing blob with same checksum" do
    # Create first blob
    blob1 = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io1,
      filename: "test1.jpg",
      content_type: "image/jpeg"
    )

    # Create second blob with same content
    blob2 = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io2,
      filename: "test2.jpg",
      content_type: "image/jpeg"
    )

    # Should reuse the same blob
    assert_equal blob1.id, blob2.id
    assert_equal blob1.checksum, blob2.checksum
  end

  test "find_or_create_blob creates new blob for different content" do
    # Create first blob
    blob1 = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io1,
      filename: "test1.jpg",
      content_type: "image/jpeg"
    )

    # Create second blob with different content
    blob2 = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io3,
      filename: "test3.txt",
      content_type: "text/plain"
    )

    # Should create different blobs
    assert_not_equal blob1.id, blob2.id
    assert_not_equal blob1.checksum, blob2.checksum
  end

  test "find_or_create_blob handles IO that doesn't respond to rewind gracefully" do
    io = StringIO.new("test content")
    # IO will be rewound, but if it fails, the service should handle it
    blob = Services::BlobDeduplicationService.find_or_create_blob(
      io: io,
      filename: "test.txt",
      content_type: "text/plain"
    )

    assert blob.persisted?
  end

  test "find_or_create_blob falls back on error" do
    # Mock ActiveStorage::Blob to raise an error first time
    original_compute = ActiveStorage::Blob.method(:compute_checksum)
    ActiveStorage::Blob.stubs(:compute_checksum).raises(StandardError.new("Checksum error"))
    ActiveStorage::Blob.stubs(:find_by).returns(nil)

    # Mock create_and_upload! to work on fallback
    mock_blob = ActiveStorage::Blob.new
    mock_blob.stubs(:persisted?).returns(true)
    mock_blob.stubs(:filename).returns(ActiveStorage::Filename.new("test.jpg"))
    mock_blob.stubs(:content_type).returns("image/jpeg")
    ActiveStorage::Blob.stubs(:create_and_upload!).returns(mock_blob)

    # Should fall back and still create blob
    blob = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io1,
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    assert_not_nil blob
    
    # Restore original method
    ActiveStorage::Blob.unstub(:compute_checksum)
  end

  test "find_or_create_blob preserves filename and content_type" do
    blob = Services::BlobDeduplicationService.find_or_create_blob(
      io: @io1,
      filename: "custom_name.jpg",
      content_type: "image/png"
    )

    assert_equal "custom_name.jpg", blob.filename.to_s
    assert_equal "image/png", blob.content_type
  end
end

