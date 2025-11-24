require "test_helper"

class ComfyUiServiceTest < ActiveSupport::TestCase
  def setup
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @extraction_prompt = "Extract this item with white background"
    @original_comfy_url = ENV["COMFY_UI_API_URL"]
  end

  def teardown
    # Reset ENV variable to prevent test pollution
    ENV["COMFY_UI_API_URL"] = @original_comfy_url
  end

  # Helper method to generate valid PNG data that passes service validation
  # Service requires: valid PNG header + minimum 10,000 bytes
  def valid_png_image_data(size: 15_000)
    # PNG signature (8 bytes) - this is what the service validates
    png_header = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ].pack("C*")

    # Create a minimal valid PNG structure with enough padding to meet size requirement
    # The service only validates: PNG header (first 8 bytes) and minimum size (10,000 bytes)
    # So we create a simple structure: header + padding + minimal chunks

    # Minimal IHDR chunk: 4 bytes length + 4 bytes type + 13 bytes data + 4 bytes CRC
    ihdr_length = [ 13 ].pack("N")
    ihdr_type = "IHDR"
    # IHDR data: width (4), height (4), bit_depth (1), color_type (1), compression (1), filter (1), interlace (1)
    ihdr_data = [ 100, 100, 8, 6, 0, 0, 0 ].pack("NNCCCCC")
    ihdr_crc = [ 0 ].pack("N") # Simplified CRC for testing
    ihdr_chunk = ihdr_length + ihdr_type + ihdr_data + ihdr_crc

    # Calculate padding needed to reach desired size
    # Structure: header (8) + IHDR (25) + IDAT (4 length + 4 type + data + 4 CRC) + IEND (12)
    # IDAT structure: 4 (length) + 4 (type) + data + 4 (CRC) = 12 + data_size
    fixed_size = png_header.bytesize + ihdr_chunk.bytesize + 12 + 12 # header + IHDR + IDAT overhead + IEND
    padding_size = [ size - fixed_size, 0 ].max

    # IDAT chunk with padding
    idat_length = [ padding_size ].pack("N")
    idat_type = "IDAT"
    idat_data = "x" * padding_size
    idat_crc = [ 0 ].pack("N") # Simplified CRC for testing
    idat_chunk = idat_length + idat_type + idat_data + idat_crc

    # IEND chunk (standard PNG ending)
    iend_chunk = [ 0 ].pack("N") + "IEND" + [ 0xAE426082 ].pack("N")

    result = png_header + ihdr_chunk + idat_chunk + iend_chunk
    result.force_encoding("BINARY")
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
    VCR.turned_off do
      # Temporarily disable net connect to ensure WebMock intercepts
      WebMock.disable_net_connect!(allow_localhost: false)

      # Stub the exact endpoint that check_comfyui_availability! calls
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Errno::ECONNREFUSED)

      # Mock WebSocket connection to fail (though it shouldn't reach here)
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

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
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles timeout errors" do
    VCR.turned_off do
      # Temporarily disable net connect to ensure WebMock intercepts
      WebMock.disable_net_connect!(allow_localhost: false)

      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Net::ReadTimeout)

      # Mock WebSocket connection to fail immediately (service tries WebSocket first)
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

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
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles ComfyUI returning non-200 status" do
    VCR.turned_off do
      WebMock.stub_request(:get, /http:\/\/localhost:8188\//).to_return(status: 500)

      # Mock WebSocket connection to fail immediately (service tries WebSocket first)
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal false, result["success"]
      assert result["error"].present?
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo submits workflow successfully" do
    VCR.turned_off do
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

      # Stub polling (completed immediately for test - fallback after WebSocket fails)
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

      # Stub image download with valid PNG data
      valid_png_data = valid_png_image_data
      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      # Mock WebSocket connection to fail so it falls back to polling
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal true, result["success"]
      assert_equal job_id, result["job_id"]
      assert result["outputs"].present?
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles workflow submission failure" do
    VCR.turned_off do
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

      # Mock WebSocket connection to fail (though it shouldn't reach here due to submission failure)
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal false, result["success"]
      assert result["error"].present?
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles missing prompt_id in response" do
    VCR.turned_off do
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

      # Stub workflow submission with missing prompt_id
      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .to_return(
          status: 200,
          body: {}.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      # Mock WebSocket connection to fail (though it shouldn't reach here due to missing prompt_id)
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal false, result["success"]
      assert result["error"].present?
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles job timeout" do
    VCR.turned_off do
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

      # Stub polling to never complete (simulate timeout - fallback after WebSocket fails)
      # Service polls every 2 seconds. With timeout 2, it should try 1 time.
      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: { job_id => { "status" => { "completed" => false } } }.to_json,
          headers: { "Content-Type" => "application/json" }
        )
        .times(1) # Stub 1 polling attempt

      # Stub sleep to prevent actual 2-second delays between polls
      # This makes the test run instantly while still testing timeout logic
      # sleep is a private Kernel method available to all objects
      Object.any_instance.stubs(:sleep)

      # Mock WebSocket connection to fail so it falls back to polling
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt,
        timeout: 2 # Short timeout for test
      )

      assert_equal false, result["success"]
      assert_includes result["error"], "timed out"
    ensure
      # Clean up stubs
      Object.any_instance.unstub(:sleep) if Object.any_instance.respond_to?(:unstub)
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo handles job error status" do
    VCR.turned_off do
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

      # Stub polling with error status (fallback after WebSocket fails)
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

      # Mock WebSocket connection to fail so it falls back to polling
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      # Service catches StandardError and returns hash, so check for error response
      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal false, result["success"]
      assert_includes result["error"], "ComfyUI job failed"
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "extract_stock_photo uses custom COMFY_UI_API_URL from environment" do
    VCR.turned_off do
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

      # Stub polling (fallback after WebSocket fails)
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

      # Stub image download with valid PNG data
      valid_png_data = valid_png_image_data
      WebMock.stub_request(:get, /http:\/\/custom-host:9999\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      # Mock WebSocket connection to fail so it falls back to polling
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal true, result["success"]
    ensure
      # Restore original URL
      ENV["COMFY_UI_API_URL"] = original_url if original_url
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  # WebSocket Integration Tests
  test "extract_stock_photo falls back to polling when WebSocket fails" do
    VCR.turned_off do
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

      # Stub polling (fallback after WebSocket fails)
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

      # Stub image download with valid PNG data
      valid_png_data = valid_png_image_data
      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      # Mock WebSocket connection failure to trigger fallback
      # Stub the WebSocket::Client::Simple.connect to raise an error
      WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket connection failed"))

      result = ComfyUiService.extract_stock_photo(
        original_image_blob: @image_blob,
        extraction_prompt: @extraction_prompt
      )

      assert_equal true, result["success"]
      assert_equal job_id, result["job_id"]
      assert result["outputs"].present?
    ensure
      WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    end
  end

  test "wait_for_completion_via_websocket handles WebSocket connection errors" do
    job_id = SecureRandom.uuid

    # Mock WebSocket connection failure
    WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("Connection refused"))

    assert_raises(StandardError) do
      ComfyUiService.wait_for_completion_via_websocket(job_id, timeout: 1)
    end
  ensure
    WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
  end

  test "wait_for_completion_via_websocket handles timeout" do
    job_id = SecureRandom.uuid

    # Mock WebSocket connection (but never send completion message)
    mock_ws = mock("websocket")
    mock_ws.stubs(:on)
    mock_ws.stubs(:close)
    WebSocket::Client::Simple.stubs(:connect).returns(mock_ws)

    # Stub Timeout.timeout to raise Timeout::Error immediately
    Timeout.stubs(:timeout).raises(Timeout::Error.new("execution expired"))

    assert_raises(StandardError) do
      ComfyUiService.wait_for_completion_via_websocket(job_id, timeout: 1)
    end
  ensure
    WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
    Timeout.unstub(:timeout) if Timeout.respond_to?(:unstub)
  end

  test "handle_websocket_message processes executing message with completion" do
    job_id = SecureRandom.uuid

    # Stub fetch_job_results_after_completion
    mock_result = {
      "success" => true,
      "job_id" => job_id,
      "outputs" => {},
      "image_data" => valid_png_image_data
    }

    ComfyUiService.stubs(:fetch_job_results_after_completion).with(job_id).returns(mock_result)

    message = {
      "type" => "executing",
      "data" => {
        "node" => nil,
        "prompt_id" => job_id
      }
    }

    result = nil
    ComfyUiService.handle_websocket_message(message, job_id) do |extraction_result|
      result = extraction_result
    end

    assert_equal mock_result, result
  end

  test "handle_websocket_message ignores executing message for different job" do
    job_id = SecureRandom.uuid
    other_job_id = SecureRandom.uuid

    message = {
      "type" => "executing",
      "data" => {
        "node" => nil,
        "prompt_id" => other_job_id
      }
    }

    # Should not call fetch_job_results_after_completion for different job
    ComfyUiService.expects(:fetch_job_results_after_completion).never

    result = nil
    ComfyUiService.handle_websocket_message(message, job_id) do |extraction_result|
      result = extraction_result
    end

    assert_nil result
  end

  test "handle_websocket_message processes progress message" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "progress",
      "data" => {
        "value" => 50,
        "max" => 100
      }
    }

    # Should not raise error, just log (we can't easily test logging)
    assert_nothing_raised do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end

  test "handle_websocket_message raises error on execution_error message" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "execution_error",
      "data" => {
        "error_message" => "Processing failed",
        "message" => "Error details"
      }
    }

    assert_raises(StandardError) do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end

  test "handle_websocket_message handles execution_start message" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "execution_start",
      "data" => {}
    }

    # Should not raise error
    assert_nothing_raised do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end

  test "handle_websocket_message handles execution_cached message" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "execution_cached",
      "data" => {}
    }

    # Should not raise error
    assert_nothing_raised do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end

  test "handle_websocket_message ignores non-hash messages" do
    job_id = SecureRandom.uuid

    # Should return early for non-hash
    assert_nil ComfyUiService.handle_websocket_message("string message", job_id)
    assert_nil ComfyUiService.handle_websocket_message(nil, job_id)
    assert_nil ComfyUiService.handle_websocket_message([], job_id)
  end

  test "extract_stock_photo uses client_id for WebSocket tracking" do
    job_id = SecureRandom.uuid
    client_id = SecureRandom.uuid

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

    # Stub workflow submission - verify client_id is included
    WebMock.stub_request(:post, "http://localhost:8188/prompt")
      .with { |request|
        body = JSON.parse(request.body)
        body["client_id"].present?
      }
      .to_return(
        status: 200,
        body: { "prompt_id" => job_id }.to_json,
        headers: { "Content-Type" => "application/json" }
      )

    # Stub polling (fallback)
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
    valid_png_data = valid_png_image_data
    WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
      .to_return(
        status: 200,
        body: valid_png_data,
        headers: { "Content-Type" => "image/png" }
      )

    # Mock WebSocket to fail so we test polling path
    WebSocket::Client::Simple.stubs(:connect).raises(StandardError.new("WebSocket failed"))

    result = ComfyUiService.extract_stock_photo(
      original_image_blob: @image_blob,
      extraction_prompt: @extraction_prompt
    )

    assert_equal true, result["success"]
  ensure
    WebSocket::Client::Simple.unstub(:connect) if WebSocket::Client::Simple.respond_to?(:unstub)
  end

  test "base_url returns default when COMFY_UI_API_URL not set" do
    original_url = ENV["COMFY_UI_API_URL"]
    ENV.delete("COMFY_UI_API_URL")

    assert_equal "http://localhost:8188", ComfyUiService.base_url
  ensure
    ENV["COMFY_UI_API_URL"] = original_url if original_url
  end

  test "base_url returns custom URL from environment" do
    original_url = ENV["COMFY_UI_API_URL"]
    ENV["COMFY_UI_API_URL"] = "http://custom:9999"

    assert_equal "http://custom:9999", ComfyUiService.base_url
  ensure
    ENV["COMFY_UI_API_URL"] = original_url if original_url
  end

  test "check_comfyui_availability! raises error on connection refused" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Errno::ECONNREFUSED)

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! raises error on host unreachable" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Errno::EHOSTUNREACH)

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! raises error on socket error" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(SocketError.new("Socket error"))

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! raises error on timeout" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Net::ReadTimeout)

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! raises error on open timeout" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_raise(Net::OpenTimeout)

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! raises error on 500 status" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_return(status: 500)

      assert_raises(StandardError) do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! succeeds on 200 status" do
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_return(status: 200, body: "OK")

      assert_nothing_raised do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "check_comfyui_availability! succeeds on 404 status" do
    # 404 is still < 500, so it passes
    VCR.turned_off do
      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/")
        .to_return(status: 404)

      assert_nothing_raised do
        ComfyUiService.send(:check_comfyui_availability!)
      end
    ensure
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "upload_image uploads image successfully" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/upload/image")
        .to_return(
          status: 200,
          body: { "name" => "uploaded_image.jpg" }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      filename = ComfyUiService.send(:upload_image, @image_blob)

      assert_equal "uploaded_image.jpg", filename
    end
  end

  test "upload_image raises error on non-200 status" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/upload/image")
        .to_return(status: 500, body: "Internal Server Error")

      assert_raises(StandardError) do
        ComfyUiService.send(:upload_image, @image_blob)
      end
    end
  end

  test "upload_image raises error on invalid JSON response" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/upload/image")
        .to_return(
          status: 200,
          body: "invalid json",
          headers: { "Content-Type" => "application/json" }
        )

      assert_raises(StandardError) do
        ComfyUiService.send(:upload_image, @image_blob)
      end
    end
  end

  test "upload_image uses filename from response" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/upload/image")
        .to_return(
          status: 200,
          body: { "name" => "custom_name.png" }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      filename = ComfyUiService.send(:upload_image, @image_blob)

      assert_equal "custom_name.png", filename
    end
  end

  test "build_workflow returns workflow hash with extraction prompt" do
    workflow = ComfyUiService.send(:build_workflow, "test_image.jpg", "Extract this item")

    assert_kind_of Hash, workflow
    assert workflow["115:111"].present?
    assert_equal "Extract this item", workflow["115:111"]["inputs"]["prompt"]
    assert_equal "test_image.jpg", workflow["78"]["inputs"]["image"]
  end

  test "submit_workflow submits workflow with client_id" do
    VCR.turned_off do
      job_id = SecureRandom.uuid
      client_id = SecureRandom.uuid

      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .with { |request|
          body = JSON.parse(request.body)
          body["client_id"] == client_id && body["prompt"].present?
        }
        .to_return(
          status: 200,
          body: { "prompt_id" => job_id }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      workflow = ComfyUiService.send(:build_workflow, "test.jpg", "prompt")
      result = ComfyUiService.send(:submit_workflow, workflow, client_id: client_id)

      assert_equal job_id, result
    end
  end

  test "submit_workflow generates client_id if not provided" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .with { |request|
          body = JSON.parse(request.body)
          body["client_id"].present?
        }
        .to_return(
          status: 200,
          body: { "prompt_id" => job_id }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      workflow = ComfyUiService.send(:build_workflow, "test.jpg", "prompt")
      result = ComfyUiService.send(:submit_workflow, workflow)

      assert_equal job_id, result
    end
  end

  test "submit_workflow raises error on non-200 status" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .to_return(status: 500, body: "Internal Server Error")

      workflow = ComfyUiService.send(:build_workflow, "test.jpg", "prompt")

      assert_raises(StandardError) do
        ComfyUiService.send(:submit_workflow, workflow)
      end
    end
  end

  test "submit_workflow raises error on missing prompt_id" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .to_return(
          status: 200,
          body: {}.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      workflow = ComfyUiService.send(:build_workflow, "test.jpg", "prompt")

      assert_raises(StandardError) do
        ComfyUiService.send(:submit_workflow, workflow)
      end
    end
  end

  test "submit_workflow raises error on invalid JSON" do
    VCR.turned_off do
      WebMock.stub_request(:post, "http://localhost:8188/prompt")
        .to_return(
          status: 200,
          body: "invalid json",
          headers: { "Content-Type" => "application/json" }
        )

      workflow = ComfyUiService.send(:build_workflow, "test.jpg", "prompt")

      assert_raises(StandardError) do
        ComfyUiService.send(:submit_workflow, workflow)
      end
    end
  end

  test "poll_for_completion handles job with status_str success" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.disable_net_connect!(allow_localhost: false)
      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: {
            job_id => {
              "status" => { "status_str" => "success", "completed" => false },
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

      valid_png_data = valid_png_image_data
      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      Object.any_instance.stubs(:sleep)

      # Use timeout: 2 which means 1 attempt (interval 2)
      result = ComfyUiService.send(:poll_for_completion, job_id, timeout: 2)

      assert_equal true, result["success"]
      assert_equal job_id, result["job_id"]
    ensure
      Object.any_instance.unstub(:sleep) if Object.any_instance.respond_to?(:unstub)
      WebMock.disable_net_connect!(allow_localhost: true)
    end
  end

  test "poll_for_completion handles non-200 history response" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(status: 500)
        .times(1)

      Object.any_instance.stubs(:sleep)

      # Should continue polling (non-200 doesn't raise, just continues)
      # After max attempts, it times out. timeout: 2 => 1 attempt
      assert_raises(StandardError) do
        ComfyUiService.send(:poll_for_completion, job_id, timeout: 2, interval: 2)
      end
    ensure
      Object.any_instance.unstub(:sleep) if Object.any_instance.respond_to?(:unstub)
    end
  end

  test "poll_for_completion handles empty history response" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: {}.to_json,
          headers: { "Content-Type" => "application/json" }
        )
        .times(1)

      Object.any_instance.stubs(:sleep)

      # Empty history means job still processing, should timeout
      # timeout: 2 => 1 attempt
      assert_raises(StandardError) do
        ComfyUiService.send(:poll_for_completion, job_id, timeout: 2, interval: 2)
      end
    ensure
      Object.any_instance.unstub(:sleep) if Object.any_instance.respond_to?(:unstub)
    end
  end

  test "poll_for_completion raises error on invalid JSON" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: "invalid json",
          headers: { "Content-Type" => "application/json" }
        )

      Object.any_instance.stubs(:sleep)

      assert_raises(StandardError) do
        ComfyUiService.send(:poll_for_completion, job_id, timeout: 2)
      end
    ensure
      Object.any_instance.unstub(:sleep) if Object.any_instance.respond_to?(:unstub)
    end
  end

  test "fetch_job_results_after_completion raises error on non-200 status" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(status: 500)

      assert_raises(StandardError) do
        ComfyUiService.send(:fetch_job_results_after_completion, job_id)
      end
    end
  end

  test "fetch_job_results_after_completion raises error on missing job data" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: {}.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      assert_raises(StandardError) do
        ComfyUiService.send(:fetch_job_results_after_completion, job_id)
      end
    end
  end

  test "fetch_job_results_after_completion raises error on job failure" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: {
            job_id => {
              "status" => {
                "status_str" => "error",
                "messages" => [ "Processing failed" ]
              },
              "outputs" => {}
            }
          }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      assert_raises(StandardError) do
        ComfyUiService.send(:fetch_job_results_after_completion, job_id)
      end
    end
  end

  test "fetch_job_results_after_completion raises error on missing image data" do
    VCR.turned_off do
      job_id = SecureRandom.uuid

      WebMock.stub_request(:get, "http://localhost:8188/history/#{job_id}")
        .to_return(
          status: 200,
          body: {
            job_id => {
              "status" => { "completed" => true },
              "outputs" => {}
            }
          }.to_json,
          headers: { "Content-Type" => "application/json" }
        )

      assert_raises(StandardError) do
        ComfyUiService.send(:fetch_job_results_after_completion, job_id)
      end
    end
  end

  test "extract_image_from_outputs returns nil for empty outputs" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      http = Net::HTTP.new(base_uri.host, base_uri.port)

      result = ComfyUiService.send(:extract_image_from_outputs, {}, http, base_uri)

      assert_nil result
    end
  end

  test "extract_image_from_outputs returns nil for non-hash outputs" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      http = Net::HTTP.new(base_uri.host, base_uri.port)

      result = ComfyUiService.send(:extract_image_from_outputs, [], http, base_uri)

      assert_nil result
    end
  end

  test "extract_image_from_outputs downloads image from node 60" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      valid_png_data = valid_png_image_data

      outputs = {
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

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_not_nil result
      assert_equal valid_png_data, result
    end
  end

  test "extract_image_from_outputs returns nil on download failure" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")

      outputs = {
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

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(status: 500)

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_nil result
    end
  end

  test "extract_image_from_outputs returns nil for image too small" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      # Create PNG data smaller than 10,000 bytes
      small_png_data = valid_png_image_data(size: 5_000)

      outputs = {
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

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: small_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_nil result
    end
  end

  test "extract_image_from_outputs returns nil for invalid PNG header" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      # Create data with invalid PNG header
      invalid_png = "INVALID" + ("x" * 10_000)

      outputs = {
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

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: invalid_png,
          headers: { "Content-Type" => "image/png" }
        )

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_nil result
    end
  end

  test "extract_image_from_outputs uses fallback when node 60 not found" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      valid_png_data = valid_png_image_data

      outputs = {
        "99" => {
          "images" => [
            {
              "filename" => "fallback_output.png",
              "subfolder" => "outputs",
              "type" => "output"
            }
          ]
        }
      }

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_not_nil result
      assert_equal valid_png_data, result
    end
  end

  test "extract_image_from_outputs handles subfolder in image path" do
    VCR.turned_off do
      base_uri = URI("http://localhost:8188")
      valid_png_data = valid_png_image_data

      outputs = {
        "60" => {
          "images" => [
            {
              "filename" => "test_output.png",
              "subfolder" => "outputs",
              "type" => "output"
            }
          ]
        }
      }

      WebMock.stub_request(:get, /http:\/\/localhost:8188\/view/)
        .with { |request| request.uri.query.include?("subfolder=outputs") }
        .to_return(
          status: 200,
          body: valid_png_data,
          headers: { "Content-Type" => "image/png" }
        )

      http = Net::HTTP.new(base_uri.host, base_uri.port)
      result = ComfyUiService.send(:extract_image_from_outputs, outputs, http, base_uri)

      assert_not_nil result
    end
  end

  test "handle_websocket_message handles executing message with node present" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "executing",
      "data" => {
        "node" => "123",
        "prompt_id" => job_id
      }
    }

    # Should not call fetch_job_results_after_completion when node is present
    ComfyUiService.expects(:fetch_job_results_after_completion).never

    ComfyUiService.handle_websocket_message(message, job_id)
  end

  test "handle_websocket_message handles executing message with different prompt_id" do
    job_id = SecureRandom.uuid
    other_job_id = SecureRandom.uuid

    message = {
      "type" => "executing",
      "data" => {
        "node" => nil,
        "prompt_id" => other_job_id
      }
    }

    # Should not call fetch_job_results_after_completion for different job
    ComfyUiService.expects(:fetch_job_results_after_completion).never

    ComfyUiService.handle_websocket_message(message, job_id)
  end

  test "handle_websocket_message handles execution_error with message field" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "execution_error",
      "data" => {
        "message" => "Error from message field"
      }
    }

    assert_raises(StandardError) do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end

  test "handle_websocket_message handles execution_error with unknown error" do
    job_id = SecureRandom.uuid

    message = {
      "type" => "execution_error",
      "data" => {}
    }

    assert_raises(StandardError) do
      ComfyUiService.handle_websocket_message(message, job_id)
    end
  end
end
