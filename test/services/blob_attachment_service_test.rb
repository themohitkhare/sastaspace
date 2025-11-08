require "test_helper"

class BlobAttachmentServiceTest < ActiveSupport::TestCase
  def setup
    @user = create(:user)
    @category = create(:category, :clothing)
    @inventory_item = create(:inventory_item, user: @user, category: @category)
    @service = Services::BlobAttachmentService.new(inventory_item: @inventory_item)
  end

  test "attach_primary_image_from_blob_id attaches blob successfully" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    result = @service.attach_primary_image_from_blob_id(blob.id)

    assert result, "Should return true on success"
    assert @inventory_item.reload.primary_image.attached?, "Primary image should be attached"
    assert_equal blob.id, @inventory_item.primary_image.blob.id
  end

  test "attach_primary_image_from_blob_id returns false for invalid blob_id" do
    result = @service.attach_primary_image_from_blob_id(999999)

    assert_not result, "Should return false for invalid blob_id"
    assert_not @inventory_item.reload.primary_image.attached?, "Primary image should not be attached"
  end

  test "attach_primary_image_from_blob_id returns false for nil blob_id" do
    result = @service.attach_primary_image_from_blob_id(nil)

    assert_not result, "Should return false for nil blob_id"
  end

  test "attach_primary_image_from_file attaches uploaded file successfully" do
    # Create a proper tempfile for the uploaded file
    tempfile = Tempfile.new([ "test", ".jpg" ])
    tempfile.write("fake image data")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.jpg",
      type: "image/jpeg"
    )

    result = @service.attach_primary_image_from_file(file)

    assert result, "Should return true on success"
    assert @inventory_item.reload.primary_image.attached?, "Primary image should be attached"
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "attach_primary_image_from_file returns false for nil file" do
    result = @service.attach_primary_image_from_file(nil)

    assert_not result, "Should return false for nil file"
  end

  test "attach_additional_images_from_files attaches multiple files" do
    # Create proper tempfiles for the uploaded files
    tempfile1 = Tempfile.new([ "test1", ".jpg" ])
    tempfile1.write("fake image data 1")
    tempfile1.rewind

    tempfile2 = Tempfile.new([ "test2", ".jpg" ])
    tempfile2.write("fake image data 2")
    tempfile2.rewind

    files = [
      ActionDispatch::Http::UploadedFile.new(
        tempfile: tempfile1,
        filename: "test1.jpg",
        type: "image/jpeg"
      ),
      ActionDispatch::Http::UploadedFile.new(
        tempfile: tempfile2,
        filename: "test2.jpg",
        type: "image/jpeg"
      )
    ]

    count = @service.attach_additional_images_from_files(files)

    assert_equal 2, count, "Should attach 2 images"
    assert_equal 2, @inventory_item.reload.additional_images.count
  ensure
    tempfile1&.close
    tempfile1&.unlink
    tempfile2&.close
    tempfile2&.unlink
  end

  test "attach_additional_images_from_files handles empty array" do
    count = @service.attach_additional_images_from_files([])

    assert_equal 0, count, "Should return 0 for empty array"
  end

  test "attach_additional_images_from_files filters out non-file objects" do
    # Create proper tempfile for the uploaded file
    tempfile = Tempfile.new([ "test", ".jpg" ])
    tempfile.write("fake image data")
    tempfile.rewind

    file = ActionDispatch::Http::UploadedFile.new(
      tempfile: tempfile,
      filename: "test.jpg",
      type: "image/jpeg"
    )

    files = [
      file,
      "", # Empty string
      nil
    ]

    count = @service.attach_additional_images_from_files(files)

    assert_equal 1, count, "Should only attach valid files"
  ensure
    tempfile&.close
    tempfile&.unlink
  end

  test "handle_blob_id_from_params_or_session uses params blob_id" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    result = @service.handle_blob_id_from_params_or_session(blob.id)

    assert result, "Should return true on success"
    assert @inventory_item.reload.primary_image.attached?
  end

  test "handle_blob_id_from_params_or_session uses session blob_id when params is nil" do
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("fake image data"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )

    session = { pending_blob_id: blob.id }
    service_with_session = Services::BlobAttachmentService.new(
      inventory_item: @inventory_item,
      session: session
    )

    result = service_with_session.handle_blob_id_from_params_or_session(nil)

    assert result, "Should return true when using session blob_id"
    assert @inventory_item.reload.primary_image.attached?
    assert_nil session[:pending_blob_id], "Session blob_id should be cleared"
  end

  test "handle_blob_id_from_params_or_session returns false when both are nil" do
    result = @service.handle_blob_id_from_params_or_session(nil)

    assert_not result, "Should return false when both params and session are nil"
  end
end
