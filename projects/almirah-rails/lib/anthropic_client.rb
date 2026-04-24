# AnthropicClient — thin wrapper around the `anthropic` gem (1.x API), pointed at
# LiteLLM (the cluster-local AI gateway).
#
# LiteLLM exposes the Anthropic API protocol, so the official gem works
# transparently — just override the base URL and use the LiteLLM API key.
#
# Usage:
#   client = AnthropicClient.new
#   response = client.complete("What is in this image?")
#   response = client.vision("Tag these clothes", image_data: b64, media_type: "image/jpeg")
#
# Environment variables:
#   LITELLM_BASE_URL  — default: http://llm.sastaspace.com
#   LITELLM_API_KEY   — required in production
#   ANTHROPIC_MODEL   — default model override (optional)

# anthropic gem 1.x API (api_key:, base_url: keywords; messages.create not messages(parameters:)).
class AnthropicClient
  DEFAULT_MODEL    = ENV.fetch("ANTHROPIC_MODEL", "claude-sonnet-4-5")
  DEFAULT_BASE_URL = ENV.fetch("LITELLM_BASE_URL", "http://llm.sastaspace.com")
  MAX_TOKENS       = 1024

  def initialize(
    base_url: DEFAULT_BASE_URL,
    api_key:  ENV.fetch("LITELLM_API_KEY", "no-key-set")
  )
    @client = Anthropic::Client.new(
      api_key:  api_key,
      base_url: base_url
    )
  end

  # Send a single text prompt and return the response text.
  def complete(prompt, model: DEFAULT_MODEL, system: nil, max_tokens: MAX_TOKENS)
    params = {
      model:      model,
      max_tokens: max_tokens,
      messages:   [ { role: "user", content: prompt } ],
    }
    params[:system_] = system if system.present?

    response = @client.messages.create(**params)
    extract_text(response)
  rescue StandardError => e
    Rails.logger.error "[AnthropicClient] Error: #{e.message}"
    raise
  end

  # Send a vision prompt with one base64-encoded image.
  def vision(prompt, image_data:, media_type: "image/jpeg", model: DEFAULT_MODEL, max_tokens: MAX_TOKENS)
    params = {
      model:      model,
      max_tokens: max_tokens,
      messages: [
        {
          role: "user",
          content: [
            {
              type:   "image",
              source: {
                type:       "base64",
                media_type: media_type,
                data:       image_data,
              },
            },
            { type: "text", text: prompt },
          ],
        },
      ],
    }

    response = @client.messages.create(**params)
    extract_text(response)
  rescue StandardError => e
    Rails.logger.error "[AnthropicClient] Vision error: #{e.message}"
    raise
  end

  private

  # Extract text from an Anthropic::Models::Message response.
  # The 1.x gem returns typed objects; each text block has a .text method.
  def extract_text(response)
    response.content
            .select { |block| block.respond_to?(:text) }
            .map(&:text)
            .join("")
  rescue StandardError
    # Fallback for test doubles or older response shapes.
    response.dig("content", 0, "text") || ""
  end
end
