require_relative "boot"

require "rails"
# Pick the frameworks you want:
require "active_model/railtie"
require "active_job/railtie"
require "active_record/railtie"
require "active_storage/engine"
require "action_controller/railtie"
# require "action_mailer/railtie"
# require "action_mailbox/engine"
require "action_text/engine"
require "action_view/railtie"
# require "action_cable/engine"
# require "rails/test_unit/railtie"

# Require the gems listed in Gemfile, including any gems
# you've limited to :test, :development, or :production.
Bundler.require(*Rails.groups)

module AlmirahRails
  class Application < Rails::Application
    # Initialize configuration defaults for originally generated Rails version.
    config.load_defaults 8.1

    # Autoload lib/ but skip non-Ruby subdirs and tasks.
    config.autoload_lib(ignore: %w[assets tasks])

    # OmniAuth provider config lives in config/initializers/omniauth.rb.
    # The middleware is registered there via Rails.application.config.middleware.use.

    # Almirah is served at sastaspace.com/almirah — path-prefix routing.
    # This makes all route helpers, asset URLs, and redirect URLs emit
    # the /almirah prefix automatically.
    config.relative_url_root = "/almirah"

    # Don't auto-generate system test stubs; we write our own.
    config.generators.system_tests = nil
  end
end
