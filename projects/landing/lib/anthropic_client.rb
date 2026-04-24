# AnthropicClient — thin wrapper around the `anthropic` gem, pointed at
# LiteLLM (the cluster-local AI gateway on llm.sastaspace.com).
#
# LiteLLM exposes the Anthropic API protocol, so the official gem works
# transparently — just override the base URL and use the LiteLLM API key.
#
# Usage:
#   client = AnthropicClient.new
#   response = client.complete("What is in this image?")
#   response = client.complete("Tag these clothes", model: "gemma4:31b")
#
# Environment variables:
#   LITELLM_BASE_URL  — default: http://llm.sastaspace.com
#   LITELLM_API_KEY   — required in production
#   ANTHROPIC_MODEL   — default model override (optional)

class AnthropicClient
  DEFAULT_MODEL    = ENV.fetch("ANTHROPIC_MODEL", "claude-sonnet-4-5")
  DEFAULT_BASE_URL = ENV.fetch("LITELLM_BASE_URL", "http://llm.sastaspace.com")
  MAX_TOKENS       = 1024

  def initialize(
    base_url: DEFAULT_BASE_URL,
    api_key:  ENV.fetch("LITELLM_API_KEY", "no-key-set")
  )
    @client = Anthropic::Client.new(
      access_token: api_key,
      uri_base:     base_url
    )
  end

  # Send a single text prompt and return the response text.
  #
  # @param prompt [String]
  # @param model  [String]  defaults to DEFAULT_MODEL
  # @param system [String]  optional system prompt
  # @return [String] the assistant's reply
  def complete(prompt, model: DEFAULT_MODEL, system: nil, max_tokens: MAX_TOKENS)
    params = {
      model:      model,
      max_tokens: max_tokens,
      messages:   [ { role: "user", content: prompt } ]
    }
    params[:system] = system if system.present?

    response = @client.messages(parameters: params)
    response.dig("content", 0, "text") || ""
  rescue => e
    Rails.logger.error "[AnthropicClient] Error: #{e.message}"
    raise
  end

  # Send a vision prompt with one base64-encoded image.
  #
  # @param prompt     [String]
  # @param image_data [String]  base64-encoded image bytes
  # @param media_type [String]  "image/jpeg" | "image/png" | "image/webp" | "image/gif"
  # @param model      [String]
  # @return [String]
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
                data:       image_data
              }
            },
            { type: "text", text: prompt }
          ]
        }
      ]
    }

    response = @client.messages(parameters: params)
    response.dig("content", 0, "text") || ""
  rescue => e
    Rails.logger.error "[AnthropicClient] Vision error: #{e.message}"
    raise
  end
end
