require_relative "boot"

require "rails/all"

# Require the gems listed in Gemfile, including any gems
# you've limited to :test, :development, or :production.
Bundler.require(*Rails.groups)

module Sastaspace
  class Application < Rails::Application
    # Initialize configuration defaults for originally generated Rails version.
    config.load_defaults 8.1

    # Suppress frozen string literal warnings from gems like marcel
    # This warning comes from Ruby 3.4+ about future frozen string behavior
    # We'll handle this in an initializer to avoid affecting other Ruby processes

    # Please, add to the `ignore` list any other `lib` subdirectories that do
    # not contain `.rb` files, or that should not be reloaded or eager loaded.
    # Common ones are `templates`, `generators`, or `middleware`, for example.
    config.autoload_lib(ignore: %w[assets tasks])

    # Add app/middleware to autoload paths
    config.autoload_paths << Rails.root.join("app", "middleware")

    # Add app/services to autoload paths
    # This ensures service classes are autoloaded throughout the application
    config.autoload_paths << Rails.root.join("app", "services")

    # Configuration for the application, engines, and railties goes here.
    #
    # These settings can be overridden in specific environments using the files
    # in config/environments, which are processed later.
    #
    # config.time_zone = "Central Time (US & Canada)"
    # config.eager_load_paths << Rails.root.join("extras")

    # Use Rails' built-in request ID middleware (ActionDispatch::RequestId)
    # Custom RequestIdMiddleware is kept for unit tests but not inserted into the stack

    # Add rate limiting middleware (rack-attack) - before security headers to catch rate limits early
    config.middleware.use Rack::Attack

    # Add security headers middleware
    # Middleware needs to be required at boot time (before autoloading)
    require Rails.root.join("app", "middleware", "security_headers_middleware")
    config.middleware.use SecurityHeadersMiddleware
  end
end
