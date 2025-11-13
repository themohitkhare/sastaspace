require "test_helper"

class ComfyUiServiceTest < ActiveSupport::TestCase
  def setup
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @extraction_prompt = "Extract this item with white background"
  end

  test "extract_stock_photo raises error when image_blob is missing" do
    assert_raises(ArgumentError) do
      ComfyUiService.extract_stock_photo(
        original_image_blob: nil,
        extraction_prompt: @extraction_prompt
      )
    end
  end

  test "extract_stock_photo raises error when extraction_prompt is missing" do
    assert_raises(ArgumentError) do
      ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: nil
      )
    end
  end

  test "extract_stock_photo raises error when ComfyUI is unreachable" do
    # Temporarily disable net connect to ensure WebMock intercepts
    WebMock.disable_net_connect!(allow_localhost: false)

    # Stub the exact endpoint that check_comfyui_availability! calls
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_raise(Errno::ECONNREFUSED)

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert result["error"].present?
    assert_includes result["error"], "ComfyUI service is not available"
  ensure
    # Restore WebMock configuration
    WebMock.disable_net_connect!(allow_localhost: true)
  end

  test "extract_stock_photo handles timeout errors" do
    # Temporarily disable net connect to ensure WebMock intercepts
    WebMock.disable_net_connect!(allow_localhost: false)

    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_raise(Net::ReadTimeout)

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert result["error"].present?
    assert_includes result["error"], "Timeout connecting to ComfyUI"
  ensure
    # Restore WebMock configuration
    WebMock.disable_net_connect!(allow_localhost: true)
  end

  test "extract_stock_photo handles ComfyUI returning non-200 status" do
    WebMock.stub_request(:get, /http:\/\/localhost:8188\//).to_return(status: 500)

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert result["error"].present?
  end

  test "extract_stock_photo submits workflow successfully" do
    job_id = SecureRandom.uuid

    # Stub availability check
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_return(status: 200, body: "OK")

    # Stub image upload
    WebMock.stub_request(:post, "http://localhost:8188/upload/image")
      .to_return(
        status: 200,
        body: { "name" => "test_image.jpg" }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub workflow submission
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .to_return(
        status: 200,
        body: { "prompt_id" => job_id }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub polling (completed immediately for test)
    WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
      .to_return(
        status: 200,
        body: {
          job_id => {
            "status" => { "completed" => true },
            "outputs" => {
              "60" => {
                "images" => [
                  {
                    "filename" => "test_output.png",
                    "subfolder" => "",
                    "type" => "output"
                  }
                ]
              }
            }
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub image download
    WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
      .to_return(
        status: 200,
        body: "fake_image_data",
        headers: { "Content-Type" => "image/png" }
      )

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal true, result["success"]
    assert_equal job_id, result["job_id"]
    assert result["outputs"].present?
  end

  test "extract_stock_photo handles workflow submission failure" do
    # Stub availability check
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_return(status: 200, body: "OK")

    # Stub image upload
    WebMock.stub_request(:post, "http://localhost:8188/upload/image")
      .to_return(
        status: 200,
        body: { "name" => "test_image.jpg" }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub workflow submission failure
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .to_return(status: 500, body: "Internal Server Error")

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert result["error"].present?
  end

  test "extract_stock_photo handles missing prompt_id in response" do
    # Stub availability check
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_return(status: 200, body: "OK")

    # Stub workflow submission with missing prompt_id
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .to_return(
        status: 200,
        body: {}.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert result["error"].present?
  end

  test "extract_stock_photo handles job timeout" do
    job_id = SecureRandom.uuid

    # Stub availability check
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_return(status: 200, body: "OK")

    # Stub image upload
    WebMock.stub_request(:post, "http://localhost:8188/upload/image")
      .to_return(
        status: 200,
        body: { "name" => "test_image.jpg" }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub workflow submission
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .to_return(
        status: 200,
        body: { "prompt_id" => job_id }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub polling to never complete (simulate timeout)
    # Service polls up to 60 times, so stub all requests
    WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
      .to_return(
        status: 200,
        body: { job_id => { "status" => { "completed" => false } } }.to_json,
        headers: { "Content-Type" => "application/json" }
      )
      .times(60) # Stub all polling attempts

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert_includes result["error"], "timed out"
  end

  test "extract_stock_photo handles job error status" do
    job_id = SecureRandom.uuid

    # Stub availability check
    WebMock.stub_request(:get, "http://localhost:8188/")
      .to_return(status: 200, body: "OK")

    # Stub image upload
    WebMock.stub_request(:post, "http://localhost:8188/upload/image")
      .to_return(
        status: 200,
        body: { "name" => "test_image.jpg" }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub workflow submission
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .to_return(
        status: 200,
        body: { "prompt_id" => job_id }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub polling with error status
    # ComfyUI returns status with status_str: "error" and messages array
    WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
      .to_return(
        status: 200,
        body: {
          job_id => {
            "status" => {
              "status_str" => "error",
              "completed" => false,
              "messages" => [ "Processing failed" ]
            },
            "outputs" => {}
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Service catches StandardError and returns hash, so check for error response
    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal false, result["success"]
    assert_includes result["error"], "ComfyUI job failed"
  end

  test "extract_stock_photo uses custom COMFY_UI_API_URL from environment" do
    original_url = ENV["COMFY_UI_API_URL"]
    ENV["COMFY_UI_API_URL"] = "http://custom-host:9999"

    # Stub availability check on custom URL
    WebMock.stub_request(:get, "http://custom-host:9999/")
      .to_return(status: 200, body: "OK")

    # Stub image upload
    WebMock.stub_request(:post, "http://custom-host:9999/upload/image")
      .to_return(
        status: 200,
        body: { "name" => "test_image.jpg" }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    job_id = SecureRandom.uuid

    # Stub workflow submission
    WebMock.stub_request(:post, "http://custom-host:9999/prompt")
      .to_return(
        status: 200,
        body: { "prompt_id" => job_id }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub polling
    WebMock.stub_request(:get, "http://custom-host:9999/history/#{job_id}")
      .to_return(
        status: 200,
        body: {
          job_id => {
            "status" => { "completed" => true },
            "outputs" => {
              "60" => {
                "images" => [
                  {
                    "filename" => "test_output.png",
                    "subfolder" => "",
                    "type" => "output"
                  }
                ]
              }
            }
          }
        }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub image download
    WebMock.stub_request(:get, /http:\/\/custom-host:9999\/view/)
      .to_return(
        status: 200,
        body: "fake_image_data",
        headers: { "Content-Type" => "image/png" }
      )

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal true, result["success"]

    # Restore original URL
    ENV["COMFY_UI_API_URL"] = original_url
  end
end
