# FactoryBot configuration for Minitest
require "factory_bot"

class ActiveSupport::TestCase
  include FactoryBot::Syntax::Methods
end

# Configure FactoryBot
FactoryBot.definition_file_paths = %w[test/factories]
