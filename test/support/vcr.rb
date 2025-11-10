# WebMock and VCR configuration for external API testing
require "webmock/minitest"
require "vcr"

# Configure VCR
VCR.configure do |config|
  config.cassette_library_dir = "test/vcr_cassettes"
  config.hook_into :webmock

  # Filter sensitive data
  config.filter_sensitive_data("<API_KEY>") { ENV["API_KEY"] }
  config.filter_sensitive_data("<OLLAMA_HOST>") { ENV["OLLAMA_HOST"] || "http://localhost:11434" }

  # Allow localhost connections for development
  config.ignore_localhost = true
end

# Configure WebMock
# Allow real Ollama connections when ENABLE_OLLAMA_TESTS is set
if ENV["ENABLE_OLLAMA_TESTS"] == "true"
  # Allow all localhost connections for Ollama testing
  WebMock.allow_net_connect!(net_http_connect_on_start: true)
else
  # Block external connections in normal tests
  WebMock.disable_net_connect!(allow_localhost: true)
end

# Ollama API stubs for testing
class OllamaStubs
  def self.setup_image_analysis_stub(response_body = nil)
    response_body ||= {
      "model" => "llava",
      "created_at" => "2025-01-25T10:30:00Z",
      "response" => "This is a blue cotton t-shirt with a casual style. It appears to be a basic crew neck design suitable for everyday wear.",
      "done" => true
    }

    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_return(
        status: 200,
        headers: { "Content-Type" => "application/json" },
        body: response_body.to_json
      )
  end

  def self.setup_image_analysis_error_stub
    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_return(
        status: 500,
        headers: { "Content-Type" => "application/json" },
        body: { "error" => "Internal server error" }.to_json
      )
  end

  def self.setup_ollama_unavailable_stub
    WebMock.stub_request(:post, /.*\/api\/generate/)
      .to_raise(Errno::ECONNREFUSED)
  end
end

# Include WebMock in all test cases
class ActiveSupport::TestCase
  include WebMock::API

  def setup
    super
    WebMock.reset!
  end

  def teardown
    WebMock.reset!
    super
  end
end
