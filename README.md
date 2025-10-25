# SastaSpace - Fashion AI Assistant

A Rails-based backend for managing digital closets with AI-powered clothing analysis.

## Local Development

### Prerequisites

- Ruby 3.3+
- Rails 8.1+
- SQLite3
- Node.js (for asset pipeline)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd sastaspace

# Install dependencies
bundle install

# Setup database
bin/rails db:setup

# Start the development server
bin/dev
```

## Local CI Pipeline

This project uses Rails' local-first CI approach with no cloud dependency. All quality gates run locally on developer machines.

### Running Local CI

```bash
# Run the complete CI pipeline
bin/ci
```

The CI pipeline includes:

1. **Setup** - Database and dependencies setup
2. **Style: Ruby** - RuboCop linting
3. **Security: Gem audit** - Bundler-audit for vulnerable gems
4. **Security: Importmap vulnerability audit** - Importmap security check
5. **Security: Brakeman code analysis** - Static security analysis
6. **Tests: Rails** - Full test suite with coverage
7. **Tests: Seeds** - Database seeding verification
8. **Coverage: Summary** - Coverage report generation

### Individual CI Steps

You can run individual steps:

```bash
# Style checking
bin/rubocop

# Security audits
bin/bundler-audit
bin/importmap audit
bin/brakeman

# Tests
bin/rails test

# Database operations
bin/rails db:seed:replant
```

### Coverage Reports

Test coverage reports are generated in the `coverage/` directory. The CI enforces a minimum coverage threshold of 85%.

## Testing

### Test-Driven Development (TDD)

This project follows TDD principles:

1. **Red Phase** - Write failing tests first
2. **Green Phase** - Implement minimal code to pass tests
3. **Refactor Phase** - Improve code while keeping tests green

### Running Tests

```bash
# Run all tests
bin/rails test

# Run with coverage
COVERAGE=true bin/rails test

# Run specific test files
bin/rails test test/models/user_test.rb
bin/rails test test/integration/api/v1/auth_test.rb
```

### Test Structure

- **Model Tests** - Unit tests for ActiveRecord models
- **Integration Tests** - API endpoint testing
- **Service Tests** - Business logic testing
- **Job Tests** - Background job testing

## Architecture

### Models

- **User** - User authentication and profiles
- **ClothingItem** - Individual clothing pieces
- **Outfit** - Collections of clothing items
- **AiAnalysis** - AI-powered clothing analysis results

### Services

- **Ollama::ImageAnalyzer** - AI image analysis integration
- **RateLimiter** - API rate limiting
- **HealthChecker** - Application health monitoring

### API Endpoints

All API endpoints are namespaced under `/api/v1/`:

- **Authentication** - `/api/v1/auth/*`
- **Clothing Items** - `/api/v1/clothing_items`
- **Outfits** - `/api/v1/outfits`
- **AI Analysis** - `/api/v1/ai/*`

## Security & Privacy

- JWT-based authentication
- Rate limiting on all endpoints
- Input validation and sanitization
- GDPR compliance features
- Secure file upload handling

## Deployment

This application is designed for containerized deployment using Kamal.

```bash
# Deploy to production
bin/kamal deploy
```

## Contributing

1. Write failing tests first (TDD)
2. Run local CI: `bin/ci`
3. Ensure all tests pass and coverage meets threshold
4. Submit pull request

## License

[License information]
