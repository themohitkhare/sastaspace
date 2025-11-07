require "test_helper"

class ExportUserDataJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @job_id = SecureRandom.uuid
  end

  test "performs export and creates file" do
    # Create some user data
    item = create(:inventory_item, user: @user)
    outfit = create(:outfit, user: @user)

    # Perform job directly (not via perform_later) to ensure it runs synchronously
    ExportUserDataJob.new.perform(@user.id, @job_id)

    # Check job status
    status = ExportUserDataJob.get_status(@job_id, @user.id)
    assert_equal "completed", status["status"], "Status was: #{status.inspect}"
    assert status["file_path"].present?

    # Verify file exists
    assert File.exist?(status["file_path"])

    # Verify file content
    export_data = JSON.parse(File.read(status["file_path"]))
    assert_equal @user.id, export_data["export_metadata"]["user_id"]
    assert export_data["inventory_items"].any?
    assert export_data["outfits"].any?
  end

  test "handles errors gracefully" do
    # Use invalid user ID - perform directly
    ExportUserDataJob.new.perform(999999, @job_id)

    status = ExportUserDataJob.get_status(@job_id, 999999)
    assert_equal "failed", status["status"], "Status was: #{status.inspect}"
    assert status["error"].present?
    assert_equal "User not found", status["error"]
  end
end
