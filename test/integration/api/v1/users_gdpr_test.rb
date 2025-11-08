require "test_helper"
require "zip"
require "tempfile"

class Api::V1::UsersGdprTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper
  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
  end

  test "POST /api/v1/users/export initiates data export" do
    post "/api/v1/users/export",
         headers: api_v1_headers(@token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["job_id"].present?
    assert_equal "processing", body["data"]["status"]
  end

  test "GET /api/v1/users/export/status returns job status" do
    # First initiate export
    post "/api/v1/users/export",
         headers: api_v1_headers(@token)
    job_id = json_response["data"]["job_id"]

    # Perform the job synchronously for test
    perform_enqueued_jobs

    # Check status (should be completed after job runs)
    get "/api/v1/users/export/status",
        params: { job_id: job_id },
        headers: api_v1_headers(@token)

    assert_response :success
    body = json_response
    assert body["success"]
    assert_includes %w[processing completed], body["data"]["status"]
  end

  test "GET /api/v1/users/export/status requires job_id" do
    get "/api/v1/users/export/status",
        headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "MISSING_JOB_ID", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete requires password confirmation" do
    delete "/api/v1/users/delete",
           headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "CONFIRMATION_REQUIRED", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete with invalid password returns error" do
    delete "/api/v1/users/delete",
           params: { password: "wrong_password" }.to_json,
           headers: api_v1_headers(@token)

    assert_response :unauthorized
    body = json_response
    assert_not body["success"]
    assert_equal "INVALID_PASSWORD", body["error"]["code"]
  end

  test "DELETE /api/v1/users/delete with valid password initiates deletion" do
    password = "Password123!"
    user = create(:user, password: password)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    delete "/api/v1/users/delete",
           params: { password: password }.to_json,
           headers: api_v1_headers(token)

    assert_response :accepted
    body = json_response
    assert body["success"]
    assert body["data"]["message"].present?
  end

  test "GET /api/v1/users/export/download returns ZIP file" do
    # Create user data with images
    item = create(:inventory_item, user: @user)
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "test_image.jpg",
        content_type: "image/jpeg"
      )
    end

    # Initiate export
    post "/api/v1/users/export",
         headers: api_v1_headers(@token)
    job_id = json_response["data"]["job_id"]

    # Perform the job
    perform_enqueued_jobs

    # Download the export
    get "/api/v1/users/export/download",
        params: { job_id: job_id },
        headers: api_v1_headers(@token)

    assert_response :success
    assert_match(/^application\/zip/, @response.content_type.to_s, "Response should be ZIP format")
    assert_match(/attachment; filename="sastaspace_export_\d+_\d+\.zip"/, @response.headers["Content-Disposition"].to_s)

    # Verify ZIP contents
    zip_data = @response.body
    temp_zip = Tempfile.new([ "export", ".zip" ])
    temp_zip.binmode
    temp_zip.write(zip_data)
    temp_zip.rewind

    Zip::File.open(temp_zip.path) do |zip_file|
      # Verify data.json exists
      assert zip_file.find_entry("data.json"), "ZIP should contain data.json"

      # Verify JSON content
      export_data = JSON.parse(zip_file.read("data.json"))
      assert_equal @user.id, export_data["export_metadata"]["user_id"]
      assert export_data["inventory_items"].any?

      # Verify images if image was attached
      if File.exist?(test_image_path)
        image_entries = zip_file.entries.select { |e| e.name.start_with?("images/") && !e.directory? }
        assert image_entries.any?, "ZIP should contain images"
      end
    end

    temp_zip.close
    temp_zip.unlink
  end

  test "GET /api/v1/users/export/download requires job_id" do
    get "/api/v1/users/export/download",
        headers: api_v1_headers(@token)

    assert_response :bad_request
    body = json_response
    assert_not body["success"]
    assert_equal "MISSING_JOB_ID", body["error"]["code"]
  end

  test "GET /api/v1/users/export/download rejects invalid job_id" do
    get "/api/v1/users/export/download",
        params: { job_id: "invalid_job_id" },
        headers: api_v1_headers(@token)

    assert_response :not_found
    body = json_response
    assert_not body["success"]
    assert_equal "EXPORT_NOT_READY", body["error"]["code"]
  end

  test "GET /api/v1/users/export/download prevents access to other users exports" do
    # Create another user and their export
    other_user = create(:user)
    other_job_id = SecureRandom.uuid
    ExportUserDataJob.new.perform(other_user.id, other_job_id)

    # Try to download other user's export
    get "/api/v1/users/export/download",
        params: { job_id: other_job_id },
        headers: api_v1_headers(@token)

    assert_response :not_found
    body = json_response
    assert_not body["success"]
  end

  test "export with no data creates valid ZIP" do
    # User with no data
    empty_user = create(:user)
    empty_token = Auth::JsonWebToken.encode_access_token(user_id: empty_user.id)

    post "/api/v1/users/export",
         headers: api_v1_headers(empty_token)
    job_id = json_response["data"]["job_id"]

    perform_enqueued_jobs

    # Download and verify
    get "/api/v1/users/export/download",
        params: { job_id: job_id },
        headers: api_v1_headers(empty_token)

    assert_response :success

    zip_data = @response.body
    temp_zip = Tempfile.new([ "export", ".zip" ])
    temp_zip.binmode
    temp_zip.write(zip_data)
    temp_zip.rewind

    Zip::File.open(temp_zip.path) do |zip_file|
      assert zip_file.find_entry("data.json"), "ZIP should contain data.json even with no data"
      export_data = JSON.parse(zip_file.read("data.json"))
      assert_equal empty_user.id, export_data["export_metadata"]["user_id"]
      assert_equal [], export_data["inventory_items"]
      assert_equal [], export_data["outfits"]
    end

    temp_zip.close
    temp_zip.unlink
  end

  test "export includes all inventory item images" do
    # Create item with multiple images
    item = create(:inventory_item, user: @user)
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "primary.jpg",
        content_type: "image/jpeg"
      )
      item.additional_images.attach(
        io: File.open(test_image_path),
        filename: "additional1.jpg",
        content_type: "image/jpeg"
      )
      item.additional_images.attach(
        io: File.open(test_image_path),
        filename: "additional2.jpg",
        content_type: "image/jpeg"
      )
    end

    post "/api/v1/users/export",
         headers: api_v1_headers(@token)
    job_id = json_response["data"]["job_id"]

    perform_enqueued_jobs

    get "/api/v1/users/export/download",
        params: { job_id: job_id },
        headers: api_v1_headers(@token)

    assert_response :success

    zip_data = @response.body
    temp_zip = Tempfile.new([ "export", ".zip" ])
    temp_zip.binmode
    temp_zip.write(zip_data)
    temp_zip.rewind

    Zip::File.open(temp_zip.path) do |zip_file|
      if File.exist?(test_image_path)
        image_entries = zip_file.entries.select { |e| e.name.start_with?("images/") && !e.directory? }
        # Should have primary + 2 additional = 3 images
        assert image_entries.length >= 3, "ZIP should contain all images (primary + additional)"
      end
    end

    temp_zip.close
    temp_zip.unlink
  end

  test "DELETE /api/v1/users/delete actually deletes user data" do
    password = "Password123!"
    user = create(:user, password: password)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    # Create user data
    item = create(:inventory_item, user: user)
    outfit = create(:outfit, user: user)
    analysis = create(:ai_analysis, inventory_item: item)

    user_id = user.id

    # Delete account
    delete "/api/v1/users/delete",
           params: { password: password }.to_json,
           headers: api_v1_headers(token)

    assert_response :accepted

    # Perform deletion job
    perform_enqueued_jobs

    # Verify user and data are deleted
    assert_nil User.find_by(id: user_id)
    assert_equal 0, InventoryItem.where(user_id: user_id).count
    assert_equal 0, Outfit.where(user_id: user_id).count
    assert_equal 0, AiAnalysis.where(inventory_item_id: item.id).count
  end

  test "DELETE /api/v1/users/delete with images removes all attachments" do
    password = "Password123!"
    user = create(:user, password: password)
    token = Auth::JsonWebToken.encode_access_token(user_id: user.id)

    # Create item with images
    item = create(:inventory_item, user: user)
    test_image_path = Rails.root.join("test", "fixtures", "files", "test_image.jpg")
    if File.exist?(test_image_path)
      item.primary_image.attach(
        io: File.open(test_image_path),
        filename: "test.jpg",
        content_type: "image/jpeg"
      )
      primary_blob_id = item.primary_image.blob.id
    end

    user_id = user.id

    delete "/api/v1/users/delete",
           params: { password: password }.to_json,
           headers: api_v1_headers(token)

    perform_enqueued_jobs

    # Verify blob is purged
    if File.exist?(test_image_path)
      assert_nil ActiveStorage::Blob.find_by(id: primary_blob_id), "Image blob should be purged"
    end
  end

  test "GDPR endpoints require authentication" do
    post "/api/v1/users/export"
    assert_response :unauthorized

    get "/api/v1/users/export/status", params: { job_id: "test" }
    assert_response :unauthorized

    get "/api/v1/users/export/download", params: { job_id: "test" }
    assert_response :unauthorized

    delete "/api/v1/users/delete", params: { password: "test" }.to_json
    assert_response :unauthorized
  end

  private

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!("Authorization" => "Bearer #{token}") if token
    headers
  end

  def json_response
    JSON.parse(@response.body)
  end
end
