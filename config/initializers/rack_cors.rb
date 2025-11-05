# Be sure to restart your server when you modify this file.

# Avoid CORS issues when API is called from the frontend app.
# Handle Cross-Origin Resource Sharing (CORS) in order to accept cross-origin AJAX requests.

# Read more: https://github.com/cyu/rack-cors

Rails.application.config.middleware.insert_before 0, Rack::Cors do
  allow do
    origins do |origin, request|
      # Allow requests from localhost in development
      if Rails.env.development?
        origin.nil? || origin.match?(/^https?:\/\/localhost(:\d+)?$/) || origin.match?(/^https?:\/\/127\.0\.0\.1(:\d+)?$/)
      else
        # In production, specify allowed origins
        # You should replace this with your actual frontend domain(s)
        allowed_origins = ENV.fetch("CORS_ALLOWED_ORIGINS", "").split(",").map(&:strip)
        allowed_origins.include?(origin)
      end
    end

    resource "/api/*",
      headers: :any,
      methods: [ :get, :post, :put, :patch, :delete, :options, :head ],
      credentials: true

    # Allow health check endpoints
    resource "/up",
      headers: :any,
      methods: [ :get, :head ]

    resource "/health",
      headers: :any,
      methods: [ :get, :head ]

    resource "/ready",
      headers: :any,
      methods: [ :get, :head ]
  end
end
