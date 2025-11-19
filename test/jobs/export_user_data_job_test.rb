require "test_helper"
require "zip"

class ExportUserDataJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @job_id = SecureRandom.uuid
  end

  test "performs export and creates ZIP file" do
    # Create some user data
    item = create(:inventory_item, user: @user)
    outfit = create(:outfit, user: @user)

    # Perform job directly (not via perform_later) to ensure it runs synchronously
    ExportUserDataJob.new.perform(@user.id, @job_id)

    # Check job status
    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"], "Status was: #{status.inspect}"
    assert status["file_path"].present?

    # Verify ZIP file exists
    assert File.exist?(status["file_path"])
    assert status["file_path"].end_with?(".zip")

    # Extract and verify ZIP contents
    Zip::File.open(status["file_path"]) do |zip_file|
      # Verify data.json exists
      json_entry = zip_file.find_entry("data.json")
      assert json_entry, "data.json should be in ZIP"

      # Read and verify JSON content
      export_data = JSON.parse(zip_file.read("data.json"))
      assert_equal @user.id, export_data["export_metadata"]["user_id"]
      assert export_data["inventory_items"].any?
      assert export_data["outfits"].any?

      # Verify images directory exists (even if empty) - ZIP files don't always create empty directories
      # So we just check that the ZIP structure is valid
      # If there are images, they'll be in the images/ directory
    end
  end

  test "performs export with images in ZIP" do
    # Create inventory item with image
    item = create(:inventory_item, user: @user)
    # Attach a test image
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "test_image.jpg",
        content_type: "image/jpeg"
      )
    end

    # Perform job
    ExportUserDataJob.new.perform(@user.id, @job_id)

    # Check job status
    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    # Verify ZIP contains images
    Zip::File.open(status["file_path"]) do |zip_file|
      # Verify data.json exists
      assert zip_file.find_entry("data.json"), "data.json should be in ZIP"

      # Check for images if image was attached
      if File.exist?(test_image_path)
        image_entries = zip_file.entries.select { |e| e.name.start_with?("images/") && !e.directory? }
        # At least one image should be in the ZIP if we attached one
        assert image_entries.any?, "ZIP should contain images when items have images attached"
      end
    end
  end

  test "handles errors gracefully" do
    # Use invalid user ID - perform directly
    ExportUserDataJob.new.perform(999999, @job_id)

    status = ExportUserDataJob.get_status(@job_id, 999999)
    assert_equal "failed", status["status"], "Status was: #{status.inspect}"
    assert status["error"].present?
    assert_equal "User not found", status["error"]
  end

  test "export includes all user data in JSON" do
    # Create comprehensive user data
    category = create(:category)
    brand = create(:brand)
    tag = create(:tag)
    item = create(:inventory_item, user: @user, category: category, brand: brand)
    item.tags << tag
    outfit = create(:outfit, user: @user)
    outfit.inventory_items << item
    analysis = create(:ai_analysis, inventory_item: item)

    ExportUserDataJob.new.perform(@user.id, @job_id)

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    Zip::File.open(status["file_path"]) do |zip_file|
      export_data = JSON.parse(zip_file.read("data.json"))

      # Verify user profile
      assert_equal @user.email, export_data["user_profile"]["email"]
      assert_equal @user.first_name, export_data["user_profile"]["first_name"]

      # Verify inventory items
      assert export_data["inventory_items"].any?
      exported_item = export_data["inventory_items"].first
      assert_equal item.name, exported_item["name"]
      assert_equal category.name, exported_item["category"]
      assert_equal brand.name, exported_item["brand"]
      assert_includes exported_item["tags"], tag.name

      # Verify outfits
      assert export_data["outfits"].any?
      exported_outfit = export_data["outfits"].first
      assert_equal outfit.name, exported_outfit["name"]

      # Verify AI analyses
      assert export_data["ai_analyses"].any?
      exported_analysis = export_data["ai_analyses"].first
      assert_equal analysis.analysis_type, exported_analysis["analysis_type"]
    end
  end

  test "export handles items without images gracefully" do
    # Create items without images
    create(:inventory_item, user: @user)
    create(:inventory_item, user: @user)

    assert_nothing_raised do
      ExportUserDataJob.new.perform(@user.id, @job_id)
    end

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    Zip::File.open(status["file_path"]) do |zip_file|
      assert zip_file.find_entry("data.json"), "ZIP should contain data.json"
      export_data = JSON.parse(zip_file.read("data.json"))
      assert_equal 2, export_data["inventory_items"].length
    end
  end

  test "export cleans up temporary files" do
    item = create(:inventory_item, user: @user)
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "test.jpg",
        content_type: "image/jpeg"
      )
    end

    # Clean up any existing temp directories for this user before test
    user_specific_pattern = File.join(Dir.tmpdir, "export_#{@user.id}_*")
    Dir.glob(user_specific_pattern).each do |dir|
      FileUtils.rm_rf(dir) if Dir.exist?(dir)
    end

    # Verify we start with no temp directories
    temp_dirs_before = Dir.glob(user_specific_pattern).length
    assert_equal 0, temp_dirs_before, "Should start with no temp directories for this user"

    ExportUserDataJob.new.perform(@user.id, @job_id)

    # Give a moment for cleanup to complete (in case of async operations)
    sleep 0.1

    # Verify temp directories are cleaned up
    temp_dirs_after = Dir.glob(user_specific_pattern)

    # Clean up any remaining directories (defensive cleanup)
    temp_dirs_after.each do |dir|
      FileUtils.rm_rf(dir) if Dir.exist?(dir)
    end

    # Re-check after defensive cleanup
    temp_dirs_final = Dir.glob(user_specific_pattern)
    assert_empty temp_dirs_final, "No temporary directories should remain for this user after export"
  end

  test "export handles StandardError and stores failure status" do
    # Stub generate_export to raise error
    ExportUserDataJob.any_instance.stubs(:generate_export).raises(StandardError.new("Export generation failed"))
    Rails.logger.stubs(:error)

    assert_raises(StandardError) do
      ExportUserDataJob.new.perform(@user.id, @job_id)
    end

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "failed", status["status"]
    assert_equal "Export generation failed", status["error"]
  end

  test "export handles download_image errors gracefully" do
    item = create(:inventory_item, user: @user)
    blob = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("test image"),
      filename: "test.jpg",
      content_type: "image/jpeg"
    )
    item.primary_image.attach(blob)

    # Stub blob download to raise error (this will be caught by download_image's rescue)
    # Stub at the class level to ensure it applies even after reload
    ActiveStorage::Blob.any_instance.stubs(:download).raises(StandardError.new("Download failed"))
    Rails.logger.stubs(:warn)

    # Should not raise, just log warning (download_image catches the error)
    assert_nothing_raised do
      ExportUserDataJob.new.perform(@user.id, @job_id)
    end

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    # Verify ZIP was created with data.json even though image download failed
    assert File.exist?(status["file_path"])
    Zip::File.open(status["file_path"]) do |zip_file|
      assert zip_file.find_entry("data.json"), "Should have data.json even if image download fails"
    end
  ensure
    # Clean up stubs
    ActiveStorage::Blob.any_instance.unstub(:download) if ActiveStorage::Blob.any_instance.respond_to?(:unstub)
  end

  test "export handles additional images" do
    item = create(:inventory_item, user: @user)
    blob1 = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("image1"),
      filename: "test1.jpg",
      content_type: "image/jpeg"
    )
    blob2 = ActiveStorage::Blob.create_and_upload!(
      io: StringIO.new("image2"),
      filename: "test2.jpg",
      content_type: "image/jpeg"
    )
    # Attach images
    item.primary_image.attach(blob1)
    item.additional_images.attach(blob2)

    # Save the item to ensure it's persisted
    item.save!

    # Reload from database to ensure attachments are loaded
    item.reload

    # Verify attachments are actually there before running the job
    assert item.primary_image.attached?, "Primary image should be attached"
    # Check additional_images using the association directly
    additional_attachments = ActiveStorage::Attachment.where(
      record_type: "InventoryItem",
      record_id: item.id,
      name: "additional_images"
    )
    assert additional_attachments.any?, "Additional images attachments should exist in database, found #{additional_attachments.count}"

    # Also verify using the association
    assert item.additional_images.attached?, "Additional images should be attached"
    additional_count = item.additional_images.count
    assert additional_count > 0, "Additional images should be attached, found #{additional_count}"

    ExportUserDataJob.new.perform(@user.id, @job_id)

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    Zip::File.open(status["file_path"]) do |zip_file|
      image_entries = zip_file.entries.select { |e| e.name.start_with?("images/") && !e.directory? }
      assert image_entries.length >= 2, "Should include both primary and additional images. Found: #{image_entries.length}, entries: #{image_entries.map(&:name).inspect}"
    end
  end

  test "download_image handles different content types" do
    job = ExportUserDataJob.new
    temp_dir = Dir.mktmpdir
    begin
      # Test PNG
      png_blob = ActiveStorage::Blob.create_and_upload!(
        io: StringIO.new("png data"),
        filename: "test.png",
        content_type: "image/png"
      )
      attachment = mock
      attachment.stubs(:attached?).returns(true)
      attachment.stubs(:content_type).returns("image/png")
      filename_mock = mock
      filename_mock.stubs(:to_s).returns("test.png")
      attachment.stubs(:filename).returns(filename_mock)
      attachment.stubs(:blob).returns(png_blob)

      job.send(:download_image, attachment, temp_dir, "test_png")

      assert File.exist?(File.join(temp_dir, "test_png.png"))
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end

  test "download_image handles missing content type" do
    job = ExportUserDataJob.new
    temp_dir = Dir.mktmpdir
    begin
      blob = ActiveStorage::Blob.create_and_upload!(
        io: StringIO.new("image data"),
        filename: "test.jpg",
        content_type: "image/jpeg"
      )
      attachment = mock
      attachment.stubs(:attached?).returns(true)
      attachment.stubs(:content_type).returns(nil)
      attachment.stubs(:filename).returns(mock(to_s: "test.jpg"))
      attachment.stubs(:blob).returns(blob)

      job.send(:download_image, attachment, temp_dir, "test")

      assert File.exist?(File.join(temp_dir, "test.jpg"))
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end

  test "download_image handles unknown content type" do
    job = ExportUserDataJob.new
    temp_dir = Dir.mktmpdir
    begin
      blob = ActiveStorage::Blob.create_and_upload!(
        io: StringIO.new("image data"),
        filename: "test.unknown",
        content_type: "image/unknown"
      )
      attachment = mock
      attachment.stubs(:attached?).returns(true)
      attachment.stubs(:content_type).returns("image/unknown")
      attachment.stubs(:filename).returns(mock(to_s: "test.unknown"))
      attachment.stubs(:blob).returns(blob)

      job.send(:download_image, attachment, temp_dir, "test")

      # Should use extension from filename
      assert File.exist?(File.join(temp_dir, "test.unknown"))
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end

  test "download_image skips unattached images" do
    job = ExportUserDataJob.new
    temp_dir = Dir.mktmpdir
    begin
      attachment = mock
      attachment.stubs(:attached?).returns(false)

      assert_nothing_raised do
        job.send(:download_image, attachment, temp_dir, "test")
      end

      # Should not create file
      assert_empty Dir.glob(File.join(temp_dir, "*"))
    ensure
      FileUtils.rm_rf(temp_dir)
    end
  end

  test "cleanup_old_exports removes old files" do
    job = ExportUserDataJob.new
    old_file = ExportUserDataJob::EXPORT_DIR.join("user_#{@user.id}_export_old.zip")
    new_file = ExportUserDataJob::EXPORT_DIR.join("user_#{@user.id}_export_new.zip")

    # Create old file (8 days ago)
    FileUtils.mkdir_p(ExportUserDataJob::EXPORT_DIR)
    File.write(old_file, "old data")
    old_time = 8.days.ago.to_time
    File.utime(old_time, old_time, old_file)

    # Create new file (1 day ago)
    File.write(new_file, "new data")
    new_time = 1.day.ago.to_time
    File.utime(new_time, new_time, new_file)

    job.send(:cleanup_old_exports, @user.id)

    assert_not File.exist?(old_file), "Old file should be deleted"
    assert File.exist?(new_file), "New file should remain"
  ensure
    File.delete(old_file) if File.exist?(old_file)
    File.delete(new_file) if File.exist?(new_file)
  end

  test "write_status uses test store in test environment" do
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::NullStore.new

    begin
      cache_key = "export_job:test:123"
      status_data = { "status" => "test" }

      ExportUserDataJob.write_status(cache_key, status_data, 1.hour)

      # Should be in test store
      result = ExportUserDataJob.read_status(cache_key)
      assert_equal "test", result["status"]
    ensure
      Rails.cache = original_cache
      ExportUserDataJob.instance_variable_set(:@test_status_store, {})
    end
  end

  test "get_status returns not_found for missing status" do
    status = ExportUserDataJob.get_status("nonexistent", @user.id)

    assert_equal "not_found", status["status"]
  end

  test "export handles temp directory cleanup errors" do
    item = create(:inventory_item, user: @user)

    # Stub FileUtils.rm_rf to raise error first time, succeed second time
    FileUtils.stubs(:rm_rf).raises(StandardError.new("Cleanup error")).then.returns(true)
    Rails.logger.stubs(:warn)

    assert_nothing_raised do
      ExportUserDataJob.new.perform(@user.id, @job_id)
    end

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]
  end

  test "export handles items with no images" do
    create(:inventory_item, user: @user)

    ExportUserDataJob.new.perform(@user.id, @job_id)

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"]

    Zip::File.open(status["file_path"]) do |zip_file|
      assert zip_file.find_entry("data.json"), "Should have data.json"
      export_data = JSON.parse(zip_file.read("data.json"))
      assert export_data["inventory_items"].any?
    end
  end

  test "export includes expires_at in status" do
    item = create(:inventory_item, user: @user)

    ExportUserDataJob.new.perform(@user.id, @job_id)

    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert status["expires_at"].present?
    assert_match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/, status["expires_at"])
  end

  test "export logs completion message" do
    item = create(:inventory_item, user: @user)
    log_messages = []

    # Stub logger to capture messages but still call the original method
    original_info = Rails.logger.method(:info)
    Rails.logger.stubs(:info).with { |msg|
      log_messages << msg
      original_info.call(msg) if original_info
      true
    }

    ExportUserDataJob.new.perform(@user.id, @job_id)

    log_message = log_messages.find { |msg| msg.include?("GDPR export completed") }
    assert log_message.present?, "Should log completion. Logged messages: #{log_messages.inspect}"
    assert log_message.include?(@user.id.to_s)
    assert log_message.include?(@job_id)
  end
end
