module Services
  class OutfitCritiqueService
    def self.analyze(outfit)
      new(outfit).analyze
    end

    def initialize(outfit)
      @outfit = outfit
      @user = outfit.user
    end

    def analyze
      return { error: "Outfit has no items" } if @outfit.inventory_items.empty?

      # Check for existing recent analysis
      recent_analysis = AiAnalysis.where(
        outfit: @outfit,
        analysis_type: "outfit_critique"
      ).where("created_at > ?", 1.day.ago)
       .order(created_at: :desc)
       .first

      if recent_analysis
        return format_result(recent_analysis.analysis_data)
      end

      # Generate prompt
      prompt = build_prompt

      # Call Ollama
      begin
        response = call_ollama(prompt)
      rescue StandardError => e
        Rails.logger.error "Error calling Ollama: #{e.message}"
        return { error: "AI service unavailable" }
      end

      # Store result
      if response[:success]
        AiAnalysis.create!(
          outfit: @outfit,
          user: @user,
          analysis_type: "outfit_critique",
          analysis_data: response[:data],
          confidence_score: response[:data][:score] || 0.5
        )
        format_result(response[:data])
      else
        { error: response[:error] }
      end
    end

    private

    def build_prompt
      items_desc = @outfit.inventory_items.map do |item|
        details = [ item.name, item.category&.name, item.color ].compact.join(", ")
        "- #{details}"
      end.join("\n")

      <<~PROMPT
        You are an expert fashion stylist. Analyze this outfit:

        Outfit Name: #{@outfit.name}
        Occasion: #{@outfit.occasion || 'General'}
        Season: #{@outfit.season || 'Any'}

        Items:
        #{items_desc}

        Provide a critique in JSON format with the following fields:
        - score: (0-100)
        - summary: (One sentence summary)
        - strengths: (List of 2-3 bullet points)
        - improvements: (List of 2-3 specific suggestions)
        - tone: (Encouraging but honest)

        Ensure the response is valid JSON only.
      PROMPT
    end

    def call_ollama(prompt)
      # Determine best available text model
      model = "llama3.2:latest" # Default to a lightweight text model

      begin
        # Use RubyLLM or direct HTTP if RubyLLM is not flexible enough
        # Using direct HTTP for better control over JSON mode if supported

        client = OllamaClient.new
        response = client.generate(
          model: model,
          prompt: prompt,
          format: "json",
          stream: false
        )

        if response["response"]
          { success: true, data: JSON.parse(response["response"]) }
        else
          { success: false, error: "Empty response from AI" }
        end
      rescue StandardError => e
        Rails.logger.error "Ollama Critique Error: #{e.message}"
        { success: false, error: "AI service unavailable" }
      end
    end

    def format_result(data)
      if data.is_a?(String)
        JSON.parse(data) rescue { summary: data }
      else
        data
      end
    end
  end

  # Simple internal client if not reusing a global one
  class OllamaClient
    require "net/http"
    require "uri"

    def initialize(base_url = ENV.fetch("OLLAMA_API_BASE", "http://localhost:11434"))
      @base_url = base_url
    end

    def generate(params)
      uri = URI.parse("#{@base_url}/api/generate")
      http = Net::HTTP.new(uri.host, uri.port)
      http.read_timeout = 60

      request = Net::HTTP::Post.new(uri.request_uri, { "Content-Type" => "application/json" })
      request.body = params.to_json

      response = http.request(request)

      if response.code == "200"
        JSON.parse(response.body)
      else
        raise "Ollama API Error: #{response.code} - #{response.body}"
      end
    end
  end
end
