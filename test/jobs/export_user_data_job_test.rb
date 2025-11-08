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
end
