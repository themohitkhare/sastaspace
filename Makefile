# Makefile for SastaSpace Backend

.PHONY: test test-all test-coverage lint security-check setup clean

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
	@echo "  ci             - Run all CI checks"
