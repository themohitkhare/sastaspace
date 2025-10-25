# Makefile for SastaSpace Backend

.PHONY: test test-all test-coverage lint security-check setup clean tree audit

# Run all tests
test:
	bundle exec rails test

# Run tests with coverage
test-coverage:
	COVERAGE=true bundle exec rails test

# Run specific test files
test-models:
	bundle exec rails test test/models/

test-integration:
	bundle exec rails test test/integration/

test-services:
	bundle exec rails test test/services/

test-jobs:
	bundle exec rails test test/jobs/

# Lint code
lint:
	bundle exec rubocop -A

# Security checks
security-check:
	bundle exec brakeman
	bundle exec bundle-audit check

# Setup development environment
setup:
	bundle install
	bundle exec rails db:create
	bundle exec rails db:schema:load
	bundle exec rails db:seed

# Clean up
clean:
	bundle exec rails db:drop
	bundle exec rails db:create
	bundle exec rails db:schema:load

# Print directory tree structure
tree:
	@echo "📁 SastaSpace Rails Application Structure:"
	@echo "=========================================="
	@tree -I 'node_modules|.git|coverage|tmp|log|storage|vendor|*.sqlite3*' -a --dirsfirst
	@echo ""
	@echo "📄 Rails Key Files:"
	@echo "==================="
	@find . -maxdepth 3 \( -name "*.rb" -o -name "*.yml" -o -name "*.json" -o -name "Gemfile*" -o -name "Rakefile" -o -name "Makefile" -o -name "README*" -o -name "*.js" -o -name "*.css" -o -name "*.erb" \) | grep -v './.git' | sort

# Comprehensive Rails application audit
audit:
	@echo "🔍 SastaSpace Rails Application Audit"
	@echo "===================================="
	@echo ""
	@echo "📊 Rails File Counts by Type:"
	@echo "-----------------------------"
	@echo "Models: $$(find app/models -name "*.rb" 2>/dev/null | wc -l)"
	@echo "Controllers: $$(find app/controllers -name "*.rb" 2>/dev/null | wc -l)"
	@echo "Services: $$(find app/services -name "*.rb" 2>/dev/null | wc -l)"
	@echo "Jobs: $$(find app/jobs -name "*.rb" 2>/dev/null | wc -l)"
	@echo "Views: $$(find app/views -name "*.erb" 2>/dev/null | wc -l)"
	@echo "JavaScript: $$(find app/javascript -name "*.js" 2>/dev/null | wc -l)"
	@echo "Stylesheets: $$(find app/assets/stylesheets -name "*.css" 2>/dev/null | wc -l)"
	@echo "Test files: $$(find test -name "*_test.rb" 2>/dev/null | wc -l)"
	@echo "Spec files: $$(find spec -name "*_spec.rb" 2>/dev/null | wc -l)"
	@echo "Migration files: $$(find db/migrate -name "*.rb" 2>/dev/null | wc -l)"
	@echo "Configuration files: $$(find config -name "*.yml" -o -name "*.rb" | wc -l)"
	@echo ""
	@echo "📁 Rails Directory Sizes:"
	@echo "------------------------"
	@du -sh app/ config/ db/ test/ spec/ lib/ public/ 2>/dev/null | sort -hr
	@echo ""
	@echo "🧹 Rails Cleanup Candidates:"
	@echo "--------------------------"
	@echo "Large files (>1MB):"
	@find . -type f -size +1M -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./coverage/*" -not -path "./tmp/*" -not -path "./log/*" -not -path "./storage/*" -not -path "./vendor/*" 2>/dev/null | head -10
	@echo ""
	@echo "Empty Rails directories:"
	@find app/ test/ spec/ -type d -empty 2>/dev/null | head -10
	@echo ""
	@echo "Unused/Orphaned files:"
	@echo "Models without tests:"
	@for model in $$(find app/models -name "*.rb" -not -name "application_record.rb" -not -name "concerns" 2>/dev/null); do \
		basename=$$(basename $$model .rb); \
		if [ ! -f "test/models/$$basename""_test.rb" ] && [ ! -f "spec/models/$$basename""_spec.rb" ]; then \
			echo "  $$model"; \
		fi; \
	done | head -5

# Run all checks
ci: lint security-check test-coverage

# Help
help:
	@echo "Available commands:"
	@echo "  test           - Run all tests"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  test-models    - Run model tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-services  - Run service tests only"
	@echo "  test-jobs      - Run job tests only"
	@echo "  lint           - Run RuboCop linting"
	@echo "  security-check - Run security checks"
	@echo "  setup          - Setup development environment"
	@echo "  clean          - Clean and reset database"
	@echo "  tree           - Print Rails application structure with tree"
	@echo "  audit          - Comprehensive Rails application audit and cleanup analysis"
	@echo "  ci             - Run all CI checks"
