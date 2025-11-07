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

## Database Performance & N+1 Prevention

### Bullet Gem

This project uses the [Bullet gem](https://github.com/flyerhzm/bullet) in development to detect N+1 queries and unused eager loading.

Bullet is configured to log warnings in development mode:
- **Console warnings** - Real-time notifications in the Rails console
- **Rails logger** - Logged to `log/development.log`
- **Bullet logger** - Separate log file in `log/bullet.log`

### Eager Loading Best Practices

Always eager load associations when accessing related data in serializers or views:

```ruby
# ✅ GOOD: Eager load associations
@inventory_items = current_user.inventory_items
                              .includes(:category, :brand, :tags,
                                        primary_image_attachment: :blob,
                                        additional_images_attachments: :blob)
                              .page(params[:page])

# ❌ BAD: Causes N+1 queries
@inventory_items = current_user.inventory_items.page(params[:page])
# Serializer will trigger separate queries for category, brand, tags, and images
```

### Active Storage Eager Loading

For Active Storage attachments, always eager load both the attachment and blob:

```ruby
# Eager load Active Storage attachments
.includes(primary_image_attachment: :blob,
          additional_images_attachments: :blob)
```

### Database Indexes

Key indexes for performance:
- `index_inventory_items_on_user_id` - User-scoped queries
- `index_inventory_items_on_user_id_and_created_at` - Sorted user queries
- `index_inventory_items_on_category_id` - Category filtering
- `index_inventory_items_on_created_at` - Sorting by date
- `index_categories_on_parent_id` - Hierarchical queries

### Checking for N+1 Queries

When Bullet detects N+1 queries, you'll see warnings in:
1. **Development console** - Inline warnings
2. **Logs** - `log/bullet.log` and `log/development.log`

Example warning:
```
N+1 Query detected
InventoryItem => [:category]
Add to your query: .includes(:category)
```

Always fix N+1 warnings before merging to main.

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

### API Endpoints

All API endpoints are namespaced under `/api/v1/`:

- **Authentication** - `/api/v1/auth/*`
- **Health Check** - `/api/v1/health`
- **Inventory Items** - `/api/v1/inventory_items`
- **Outfits** - `/api/v1/outfits`
- **Outfit Items** - `/api/v1/outfit_items`
- **Categories** - `/api/v1/categories`
- **AI Analysis** - `/api/v1/ai/analyses`

## API Documentation

### Base URL

All API endpoints are prefixed with `/api/v1`:

```
http://localhost:3000/api/v1
```

### Authentication

Most API endpoints require authentication via JWT tokens. Include the token in the `Authorization` header:

```bash
Authorization: Bearer <access_token>
```

#### Register a New User

```bash
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "password_confirmation": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "created_at": "2025-01-25T10:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "abc123def456..."
  },
  "message": "User created successfully",
  "timestamp": "2025-01-25T10:00:00Z"
}
```

#### Login

```bash
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "created_at": "2025-01-25T10:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "abc123def456..."
  },
  "message": "Login successful",
  "timestamp": "2025-01-25T10:00:00Z"
}
```

#### Refresh Access Token

```bash
curl -X POST http://localhost:3000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "abc123def456..."
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "xyz789ghi012..."
  },
  "timestamp": "2025-01-25T10:00:00Z"
}
```

#### Get Current User

```bash
curl -X GET http://localhost:3000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "created_at": "2025-01-25T10:00:00Z"
    }
  },
  "timestamp": "2025-01-25T10:00:00Z"
}
```

#### Logout

```bash
curl -X POST http://localhost:3000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Logout successful"
  },
  "timestamp": "2025-01-25T10:00:00Z"
}
```

### Health Check Endpoint

#### GET /api/v1/health

Check API health status (no authentication required):

```bash
curl -X GET http://localhost:3000/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "checks": {
    "database": "ok"
  },
  "timestamp": "2025-01-25T10:00:00Z"
}
```

### Error Response Format

All API errors follow a standardized format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field_name": ["Error message for this field"]
    },
    "timestamp": "2025-01-25T10:00:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

#### Common Error Codes

- `VALIDATION_ERROR` (422) - Request validation failed
- `AUTHENTICATION_ERROR` (401) - Authentication required or failed
- `NOT_FOUND` (404) - Resource not found
- `BAD_REQUEST` (400) - Invalid request format
- `RATE_LIMIT_EXCEEDED` (429) - Too many requests
- `INTERNAL_ERROR` (500) - Server error

#### Example Error Responses

**Validation Error (422):**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": ["can't be blank"],
      "password": ["is too short (minimum is 8 characters)"]
    },
    "timestamp": "2025-01-25T10:00:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

**Authentication Error (401):**
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid token",
    "details": "Token has expired",
    "timestamp": "2025-01-25T10:00:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

**Not Found Error (404):**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": {
      "model": "InventoryItem",
      "id": "999"
    },
    "timestamp": "2025-01-25T10:00:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

### Request Headers

All API requests should include:

- `Content-Type: application/json` - For POST/PUT/PATCH requests
- `Authorization: Bearer <token>` - For authenticated endpoints
- `X-Request-ID: <uuid>` - Optional, for request correlation

### Response Headers

All API responses include:

- `X-Request-ID` - Unique request identifier for correlation
- `Content-Type: application/json` - Response content type

### Pagination

List endpoints support pagination via query parameters:

- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 20, max: 100)

**Example:**
```bash
curl -X GET "http://localhost:3000/api/v1/inventory_items?page=2&per_page=10" \
  -H "Authorization: Bearer <access_token>"
```

**Paginated Response:**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "current_page": 2,
      "total_pages": 5,
      "total_count": 50,
      "per_page": 10,
      "has_next_page": true,
      "has_prev_page": true
    }
  },
  "timestamp": "2025-01-25T10:00:00Z"
}
```

### Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Default**: 100 requests per 60 seconds per user/IP
- **Rate Limit Header**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Rate Limit Exceeded**: Returns `429 Too Many Requests` with retry information

**Rate Limit Response (429):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 100,
      "period": 60,
      "retry_after": 60
    },
    "timestamp": "2025-01-25T10:00:00Z",
    "request_id": "abc123-def456-ghi789"
  }
}
```

### Request/Response Logging

All API requests and responses are logged in structured JSON format:

```json
{
  "timestamp": "2025-01-25T10:00:00Z",
  "level": "INFO",
  "message": "API request completed",
  "request_id": "abc123-def456-ghi789",
  "user_id": 1,
  "controller": "Api::V1::InventoryItemsController",
  "action": "index",
  "method": "GET",
  "path": "/api/v1/inventory_items",
  "status": 200,
  "duration_ms": 45.2
}
```

View logs:
```bash
# View all API logs
bin/dev-log "API request"

# Filter by request ID
bin/dev-log "request_id:abc123"
```

### Testing API Endpoints

Integration tests serve as living documentation. See `test/integration/api/v1/` for request/response examples:

```bash
# Run API integration tests
bin/rails test test/integration/api/v1/

# Run specific endpoint tests
bin/rails test test/integration/api/v1/auth_test.rb
```

This application includes comprehensive observability features for local development and production monitoring.

### Health Endpoints

- **GET /up** - Liveness check (simple app status)
- **GET /health** - Detailed health check (database, cache, queue, storage)
- **GET /api/v1/health** - API health check (includes Ollama service)
- **GET /ready** - Readiness check (migrations, queues, storage)

### Structured Logging

All logs are structured JSON format with correlation IDs:

```json
{
  "timestamp": "2025-10-25T17:30:00Z",
  "level": "INFO",
  "message": "Health check performed",
  "request_id": "abc123-def456",
  "user_id": 42,
  "controller": "Api::V1::HealthController",
  "action": "show",
  "healthy": true,
  "checks": ["database", "cache", "queue"]
}
```

### Metrics Collection

Metrics are collected via ActiveSupport::Notifications and logged:

- **Request metrics** - Duration, status codes, controller/action
- **Job metrics** - Queue latency, success/failure rates
- **Cache metrics** - Hit/miss rates, operation duration

### Viewing Logs

```bash
# View all logs
bin/dev-log

# Filter logs by type
bin/dev-log "METRIC"
bin/dev-log "ERROR"
bin/dev-log "request_id"

# Traditional Rails log tail
tail -f log/development.log
```

### Request Correlation

All requests include correlation IDs:
- **X-Request-ID header** - Unique identifier for each request
- **Request ID middleware** - Automatically generates/forwards IDs
- **Structured logging** - All logs include request_id for correlation

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
