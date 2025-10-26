RubyLLM.configure do |config|
  # OpenAI configuration
  config.openai_api_key = ENV["OPENAI_API_KEY"] || Rails.application.credentials.dig(:openai_api_key)
  config.openai_api_base = ENV["OPENAI_API_BASE"]
  config.openai_organization_id = ENV["OPENAI_ORGANIZATION_ID"]

  # Anthropic configuration
  config.anthropic_api_key = ENV["ANTHROPIC_API_KEY"] || Rails.application.credentials.dig(:anthropic_api_key)

  # Google Gemini configuration
  config.gemini_api_key = ENV["GEMINI_API_KEY"] || Rails.application.credentials.dig(:gemini_api_key)

  # Mistral configuration
  config.mistral_api_key = ENV["MISTRAL_API_KEY"] || Rails.application.credentials.dig(:mistral_api_key)

  # DeepSeek configuration
  config.deepseek_api_key = ENV["DEEPSEEK_API_KEY"] || Rails.application.credentials.dig(:deepseek_api_key)

  # Perplexity configuration
  config.perplexity_api_key = ENV["PERPLEXITY_API_KEY"] || Rails.application.credentials.dig(:perplexity_api_key)

  # AWS Bedrock configuration
  config.bedrock_api_key = ENV["BEDROCK_API_KEY"] || Rails.application.credentials.dig(:bedrock_api_key)
  config.bedrock_secret_key = ENV["BEDROCK_SECRET_KEY"] || Rails.application.credentials.dig(:bedrock_secret_key)
  config.bedrock_region = ENV["BEDROCK_REGION"] || "us-east-1"

  # GPUStack configuration
  config.gpustack_api_key = ENV["GPUSTACK_API_KEY"] || Rails.application.credentials.dig(:gpustack_api_key)
  config.gpustack_api_base = ENV["GPUSTACK_API_BASE"]

  # OpenRouter configuration
  config.openrouter_api_key = ENV["OPENROUTER_API_KEY"] || Rails.application.credentials.dig(:openrouter_api_key)

  # Ollama configuration
  config.ollama_api_base = ENV["OLLAMA_API_BASE"] || "http://localhost:11434"

  # Set default models
  # config.default_model = "gpt-4.1-nano"
  # config.default_embedding_model = "text-embedding-3-small"
  # config.default_image_model = "gpt-4-vision"

  # Retry configuration
  config.max_retries = (ENV["MAX_RETRIES"] || 3).to_i
  config.retry_interval = (ENV["RETRY_INTERVAL"] || 1.0).to_f
  config.request_timeout = (ENV["REQUEST_TIMEOUT"] || 120).to_i

  # Use the new association-based acts_as API (recommended)
  config.use_new_acts_as = true

  # Logging configuration
  # config.log_level = :info
  # config.log_stream_debug = false
end
