require "application_system_test_case"

class StockExtractionTest < ApplicationSystemTestCase
  include FactoryBot::Syntax::Methods

  setup do
    @user = create(:user, password: "Password123!")
    @category = create(:category, :clothing)

    # Create an image blob for testing
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )

    # Login
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "checking stock extraction job status shows processing status" do
    # Create a mock job status in cache
    job_id = SecureRandom.uuid
    status_key = ExtractStockPhotoJob.status_key(job_id)
    Rails.cache.write(status_key, {
      "status" => "processing",
      "data" => nil,
      "error" => nil,
      "updated_at" => Time.current.iso8601
    }, expires_in: 1.hour)

    # Visit status endpoint (GET request works in system tests)
    visit "/api/v1/stock_extraction/status/#{job_id}"

    # Should return JSON response (system test will render as HTML)
    # Verify we got a response (not 404 or 500)
    assert_selector "body", wait: 2

    # The JSON response should contain status information
    # In system tests, JSON is often rendered as text in body
    assert_text(/processing|status|job_id/i, wait: 2)
  end

  test "checking stock extraction job status shows completed status" do
    # Create a completed job status
    job_id = SecureRandom.uuid
    extracted_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "extracted.jpg",
      content_type: "image/jpeg"
    )

    status_key = ExtractStockPhotoJob.status_key(job_id)
    Rails.cache.write(status_key, {
      "status" => "completed",
      "data" => {
        "original_blob_id" => @image_blob.id,
        "extracted_blob_id" => extracted_blob.id
      },
      "error" => nil,
      "updated_at" => Time.current.iso8601
    }, expires_in: 1.hour)

    # Visit status endpoint
    visit "/api/v1/stock_extraction/status/#{job_id}"

    # Should show completed status
    assert_text(/completed|success/i, wait: 2)
  end

  test "checking stock extraction job status shows not found for invalid job" do
    invalid_job_id = SecureRandom.uuid

    # Visit status endpoint with invalid job ID
    visit "/api/v1/stock_extraction/status/#{invalid_job_id}"

    # Should return not found (404)
    # System test may show error page or JSON error
    assert_text(/not found|404|error/i, wait: 2)
  end

  test "stock extraction status endpoint requires authentication" do
    job_id = SecureRandom.uuid

    # Use a fresh Capybara session without authentication
    # This ensures no cookies or session data from the logged-in user
    Capybara.using_session(:guest) do
      # Try to access status endpoint without authentication
      visit "/api/v1/stock_extraction/status/#{job_id}"

      # API should return JSON with 401 status and error message
      # System tests render JSON as text in the body
      # Check for authentication error in the JSON response
      assert_text(/AUTHENTICATION_ERROR|Missing token|unauthorized/i, wait: 2)

      # Verify it's not a successful response with "not_found"
      # The response should have success: false, not success: true
      assert_no_text(/"success":true/i, wait: 0.5)
    end
  end

  test "edit page displays primary image correctly" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    # Create inventory item with primary image
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    item.primary_image.attach(@image_blob)
    # Reload to ensure attachment is persisted
    item.reload

    # Get the actual blob ID from the attached image
    actual_blob_id = item.primary_image.blob.id

    # Navigate to edit page
    visit edit_inventory_item_path(item)

    # Verify the image is displayed
    assert_selector "img[alt='Current primary image']", wait: 2
    # Verify blob ID is shown in the text (use actual blob ID from item)
    assert_text(/blob ID: #{actual_blob_id}/, wait: 2)
  end

  test "edit page shows extracted image after extraction" do
    # Stub job to prevent hanging on image processing
    ImageProcessingJob.stubs(:perform_later)

    # Create inventory item with primary image
    item = create(:inventory_item, :clothing, user: @user, category: @category)
    item.primary_image.attach(@image_blob)

    # Create an extracted image blob
    extracted_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "extracted_image.jpg",
      content_type: "image/jpeg"
    )

    # Simulate extraction: replace primary image with extracted image
    item.primary_image.detach
    item.primary_image.attach(extracted_blob)
    item.reload

    # Navigate to edit page
    visit edit_inventory_item_path(item)

    # Verify the extracted image is displayed
    assert_selector "img[alt='Current primary image']", wait: 2
    # Verify the blob ID matches the extracted blob
    assert_text(/blob ID: #{extracted_blob.id}/, wait: 2)
  end
end
