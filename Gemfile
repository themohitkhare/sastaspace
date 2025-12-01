source "https://rubygems.org"

# Bundle edge Rails instead: gem "rails", github: "rails/rails", branch: "main"
gem "rails", "~> 8.1.1"
# The modern asset pipeline for Rails [https://github.com/rails/propshaft]
gem "propshaft", "~> 1.3"
# Use PostgreSQL as the database for Active Record
gem "pg", "~> 1.6"
# Use the Puma web server [https://github.com/puma/puma]
gem "puma", "~> 7.1"
# Use JavaScript with ESM import maps [https://github.com/rails/importmap-rails]
gem "importmap-rails", "~> 2.2"
# Hotwire's SPA-like page accelerator [https://turbo.hotwired.dev]
gem "turbo-rails", "~> 2.0.20"
# Hotwire's modest JavaScript framework [https://stimulus.hotwired.dev]
gem "stimulus-rails", "~> 1.3"
# Build JSON APIs with ease [https://github.com/rails/jbuilder]
gem "jbuilder", "~> 2.14"

# Use Active Model has_secure_password [https://guides.rubyonrails.org/active_model_basics.html#securepassword]
gem "bcrypt", "~> 3.1.7"

# CORS support for API
gem "rack-cors", "~> 2.0"

# Rate limiting and blocking
gem "rack-attack", "~> 6.7"

# JWT authentication
gem "jwt", "~> 3.1"

# PostgreSQL vector search for Rails
gem "neighbor", "~> 0.6"

# RubyLLM for AI chat functionality
gem "ruby_llm", "~> 1.8"

# Pagination
gem "kaminari", "~> 1.2"

# Windows does not include zoneinfo files, so bundle the tzinfo-data gem
gem "tzinfo-data", platforms: %i[ windows jruby ]

# Use Redis for caching and Sidekiq for background jobs
gem "redis", "~> 5.0"
gem "sidekiq", "~> 8.0"
gem "solid_cable", "~> 3.0"

# Admin panel for job monitoring (optional - we use Sidekiq::Web instead)
# gem "mission_control-jobs"

# Maintenance Tasks - production-grade data migration and backfill tool
gem "maintenance_tasks"

# Reduces boot times through caching; required in config/boot.rb
gem "bootsnap", "~> 1.18", require: false

# Deploy this application anywhere as a Docker container [https://kamal-deploy.org]
gem "kamal", "~> 2.9.0", require: false

# Add HTTP asset caching/compression and X-Sendfile acceleration to Puma [https://github.com/basecamp/thruster/]
gem "thruster", "~> 0.1", require: false

# Use Active Storage variants [https://guides.rubyonrails.org/active_storage_overview.html#transforming-images]
gem "image_processing", "~> 1.2"

# Tailwind CSS for styling
# Pinned to v3 - v4 requires migration (see https://github.com/rails/tailwindcss-rails/blob/main/README.md#upgrading-your-application-from-tailwind-v3-to-v4)
gem "tailwindcss-rails", "~> 3.3.1"

# ZIP file handling for GDPR data export
gem "rubyzip", "~> 2.3"

# WebSocket client for ComfyUI real-time integration
# Latest version 0.9.0 (Dec 2024) - actively maintained, simple API
gem "websocket-client-simple", "~> 0.9"

group :development, :test do
  # See https://guides.rubyonrails.org/debugging_rails_applications.html#debugging-with-the-debug-gem
  gem "debug", "~> 1.11", platforms: %i[ mri windows ], require: "debug/prelude"

  # Audits gems for known security defects (use config/bundler-audit.yml to ignore issues)
  gem "bundler-audit", "~> 0.9", require: false

  # Static analysis for security vulnerabilities [https://brakemanscanner.org/]
  gem "brakeman", "~> 7.1.1", require: false

  # Omakase Ruby styling [https://github.com/rails/rubocop-rails-omakase/]
  gem "rubocop-rails-omakase", "~> 1.1", require: false
end

group :development do
  # Use console on exceptions pages [https://github.com/rails/web-console]
  gem "web-console", "~> 4.2"

  # Detect N+1 queries [https://github.com/flyerhzm/bullet]
  gem "bullet", "~> 8.1"
end

group :test do
  # Use system testing [https://guides.rubyonrails.org/testing.html#system-testing]
  gem "capybara", "~> 3.40"
  gem "cuprite", "~> 0.17"

  # TDD Testing Stack
  gem "factory_bot_rails", "~> 6.5"
  gem "faker", "~> 3.5"
  gem "simplecov", "~> 0.22", require: false
  gem "webmock", "~> 3.26.1"
  gem "vcr", "~> 6.3"
  gem "minitest-reporters", "~> 1.7"
  gem "shoulda-matchers", "~> 7.0.1"
  gem "mocha", "~> 2.7"
end
