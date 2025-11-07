# FactoryBot configuration for Minitest
require "factory_bot"

class ActiveSupport::TestCase
  include FactoryBot::Syntax::Methods
end

# Configure FactoryBot
FactoryBot.definition_file_paths = %w[test/factories]

# Only load definitions once per process (important for parallel tests)
# If definitions are already loaded, the duplicate definition error is harmless
begin
  FactoryBot.find_definitions
rescue FactoryBot::DuplicateDefinitionError
  # Definitions already loaded, ignore the error
end
