# SastaSpace - Fashion AI Assistant

**SastaSpace** is an intelligent digital wardrobe manager that uses local AI to help users organize their closet, generate outfit ideas, and shop smarter. Built with **Ruby on Rails 8**, it leverages **Hotwire** for a fluid frontend experience and **Ollama** for privacy-first, local AI processing.

## 🚀 Core Features

- **Digital Closet**: Organize clothes with AI-powered categorization and tagging.
- **Smart Outfit Builder**: visual canvas to mix and match items.
- **AI Stylist**:
    - **Outfit Critiques**: Get fashion advice on your combinations.
    - **Semantic Search**: Find items by description ("something for a rainy date").
    - **Color Analysis**: Auto-detect color harmony and suggestions.
- **Privacy First**: All AI processing happens locally using Ollama.
- **Hybrid Architecture**: Full-stack Hotwire UI + RESTful API for mobile clients.

---

## 🛠 Tech Stack

### Backend & Database
- **Framework**: Ruby on Rails 8.1 (Hybrid Monolith)
- **Database**: PostgreSQL with `pgvector` extension (Vector Search)
- **Jobs**: Sidekiq + Redis (Background processing)
- **Caching**: Redis
- **Asset Pipeline**: Propshaft + Tailwind CSS
- **Deployment**: Kamal (Docker-based)

### AI & Machine Learning
- **LLM Engine**: Ollama (Local inference)
- **Libraries**: `ruby_llm`, `neighbor` (Vector search)
- **Models**: `mxbai-embed-large` (Embeddings), `llava` (Vision), `llama3` (Chat)

### Frontend
- **Interactive**: Hotwire (Turbo + Stimulus)
- **CSS**: Tailwind CSS
- **Icons**: Heroicons

### Testing
- **Framework**: Minitest
- **Tools**: FactoryBot, Faker, VCR, WebMock, Mocha
- **CI**: Local-first pipeline (`bin/ci`)

---

## 💻 Local Development

### Prerequisites

- **Ruby 3.3+**
- **PostgreSQL 14+** (with `pgvector` extension)
- **Redis** (for Sidekiq & Caching)
- **Node.js** (for Tailwind/bundling)
- **Ollama** (Run locally for AI features)

### 📦 Setup

1.  **Clone & Install**:
    ```bash
    git clone <repository-url>
    cd sastaspace
    bundle install
    ```

2.  **Database Setup**:
    ```bash
    # Create DB, load schema, and seed data
    bin/rails db:setup
    ```

3.  **AI Setup (Ollama)**:
    ```bash
    # Install Ollama (https://ollama.ai)
    # Pull required models
    ollama pull mxbai-embed-large   # For vector search (REQUIRED)
    ollama pull llava:13b           # For image analysis
    ollama pull llama3.2:latest     # For outfit critiques
    ```

4.  **Start Development Server**:
    ```bash
    # Starts Rails server, Sidekiq, and Tailwind watcher
    bin/dev
    ```

Visit the app at: `http://localhost:3000`

---

## 🧪 Testing & CI

We use a **Local-First CI** approach. Run quality checks locally before pushing.

```bash
# Run full CI pipeline (Linting + Security + Tests)
bin/ci

# Run only tests
bin/rails test

# Run with coverage
COVERAGE=1 bin/rails test
```

### Test Suite
- **System Tests**: Capybara + Cuprite (Headless Chrome)
- **Integration Tests**: API & Request specs
- **Unit Tests**: Models & Services (High coverage required)

---

## 🔧 Admin & Maintenance

### Dashboards
- **Maintenance Tasks**: `/maintenance_tasks`
    - Run backfills (e.g., `BackfillEmbeddingsTask`, `BackfillStockPhotoExtractionTask`).
- **Sidekiq Web**: `/admin/jobs`
    - Monitor background queues (`default`, `ai_critical`).
    - *Note: Requires admin permissions (configured in `AdminConstraint`).*

### Common Tasks
```bash
# Re-index vector embeddings
bin/rails maintenance:tasks:run[Maintenance::BackfillEmbeddingsTask]

# Check application health
curl http://localhost:3000/up
```

---

## 🔌 API Documentation

The backend exposes a comprehensive REST API under `/api/v1/` for mobile/external clients.

### Authentication
Uses JWT (JSON Web Tokens).
- **Login**: `POST /api/v1/auth/login`
- **Register**: `POST /api/v1/auth/register`
- **Headers**: `Authorization: Bearer <token>`

### Key Endpoints
- **Inventory**: `GET /api/v1/inventory_items`
- **Outfits**: `GET /api/v1/outfits`
- **AI Analysis**: `POST /api/v1/clothing_detection/analyze`
- **Search**: `POST /api/v1/inventory_items/semantic_search`

*(See `app/controllers/api/v1/` for full endpoint list)*

---

## 🤝 Contributing

1.  **TDD**: Write failing tests first.
2.  **Lint**: Ensure `bin/rubocop` passes.
3.  **Security**: Check `bin/brakeman` for vulnerabilities.
4.  **PR**: Submit consistent, atomic commits.

## 📄 License

[MIT License]
