# CLAUDE.md — SastaSpace

## Project Overview

SastaSpace is a portfolio of interactive web projects (multiplayer board games, AI solvers, RPG builders) served from a single FastAPI backend through a Traefik reverse proxy. All frontends are React 18 + Vite + Tailwind CSS apps using a brutalist design system.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, MongoDB (async via Motor), Pydantic v2, uv (package manager)
- **Frontends**: React 18, Vite, Tailwind CSS, TypeScript
- **Reverse Proxy**: Traefik v2.11
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend), Playwright (E2E)
- **Observability**: Grafana + Loki + Promtail

## Repository Structure

```
sastaspace/
├── backend/                    # FastAPI backend (Python/uv)
│   ├── app/
│   │   ├── api/v1/             # API routers
│   │   ├── core/               # Config (pydantic-settings), logging, DB repo
│   │   ├── db/                 # MongoDB async session
│   │   └── modules/
│   │       ├── common/         # Health checks
│   │       ├── sastadice/      # Board game logic (events, services, models, schemas)
│   │       ├── sastahero/      # Hero builder API
│   │       └── sudoku/         # Genetic algorithm solver + OCR
│   ├── tests/                  # pytest suite (mirrors module structure)
│   ├── pyproject.toml          # Dependencies, tool config (ruff, mypy, pytest, coverage)
│   └── Dockerfile
├── frontends/
│   ├── shared/                 # Shared React components (Navbar, assets)
│   ├── sastaspace/             # Landing page
│   ├── sastadice/              # Board game frontend (React/Vite, bun)
│   ├── sastahero/              # Hero builder frontend (React/Vite, npm)
│   └── sudoku/                 # Sudoku frontend (React/Vite, npm)
├── grafana/                    # Grafana provisioning
├── loki/                       # Loki log aggregation config
├── promtail/                   # Log collection config
├── scripts/                    # Developer utilities
├── docker-compose.yml          # Local dev orchestration
└── Makefile                    # All build/test/CI commands
```

## Essential Commands

### Running Tests

```bash
# All tests (backend + all frontends, sequential)
make test-full

# Backend only
make test-backend                    # cd backend && uv run pytest tests/ -v

# Individual frontends
make test-frontend-sastadice         # cd frontends/sastadice && bun run test -- --run
make test-frontend-sudoku            # cd frontends/sudoku && npm run test -- --run
make test-frontend-sastahero         # cd frontends/sastahero && npm run test -- --run

# E2E tests
make test-e2e-sastadice              # Playwright
```

### Quality Gates

```bash
# Lint (ruff check + format check)
make lint

# Type checking (mypy --strict)
make typecheck

# Cyclomatic complexity (max CC=30, radon)
make complexity

# Coverage (pytest-cov, fail_under=66%)
make test-cov

# All quality gates sequentially
make audit

# All quality gates + all tests in parallel (preferred for CI)
make ci-fast
```

### Local Development

```bash
# Docker Compose — build and start everything
docker-compose up -d --build

# Backend standalone (hot-reload)
cd backend && uv sync && uv run uvicorn app.main:app --reload

# Frontend standalone (any sub-app)
cd frontends/sudoku && npm install && npm run dev
cd frontends/sastadice && bun install && bun run dev
```

## Code Style & Conventions

### Backend (Python)

- **Formatter/Linter**: ruff (line-length=100, target py311)
- **Type checking**: mypy strict mode with pydantic plugin
- **Async throughout**: All DB operations use Motor (async MongoDB driver); tests use `asyncio_mode = "auto"`
- **Test mocking**: Uses `mongomock-motor` — no real MongoDB needed for tests
- **Config**: Pydantic Settings (`app/core/config.py`), reads from env vars (MONGODB_URL, MONGODB_DATABASE, DEBUG, ENVIRONMENT)
- **Module structure**: Each module (sastadice, sastahero, sudoku) has its own models, schemas, services, and router
- **Coverage**: Branch coverage enabled, target 66% minimum (aspiring to 100%)

### Frontend (React/TypeScript)

- **Build tool**: Vite
- **Package managers**: bun (sastadice), npm (sudoku, sastahero, sastaspace)
- **State management**: Zustand (sastadice), React Query (data fetching)
- **Testing**: Vitest + React Testing Library
- **Styling**: Tailwind CSS with brutalist design aesthetic
- **Routing**: react-router-dom v7 with basename matching Traefik prefix paths

### Architecture Patterns

- **Traefik routing**: All sub-apps served through `localhost:80` with path prefixes (`/sastadice/`, `/sudoku/`, `/sastahero/`)
- **API prefix**: All backend routes under `/api/v1/`
- **CORS**: Configured for localhost origins
- **Shared components**: `frontends/shared/` contains common Navbar and assets

## Pre-Commit Hook

The repo uses a pre-commit hook that runs `make ci-fast` (all quality gates + tests in parallel). Install with:

```bash
make install-hooks
```

Skip with `git commit --no-verify` (not recommended).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGODB_DATABASE` | `sastaspace` | Database name |
| `DEBUG` | `false` | Enable debug mode |
| `ENVIRONMENT` | (not set) | `development` or `production` |

## Key API Endpoints

- `GET /api/v1/common/health` — Health check + MongoDB connectivity
- `GET /api/v1/sastahero/classes` — Hero class definitions
- `POST /api/v1/sastahero/generate` — Random hero generation
- `GET /api/v1/sudoku/matches/{id}` — Sudoku match state
- `POST /api/v1/sastadice/games` — Create new board game

## Important Notes for AI Assistants

- Always run `make ci-fast` (or at minimum the relevant subset) before considering work complete
- Backend tests require no external services (mongomock-motor mocks MongoDB)
- Frontend `sastadice` uses **bun**, while other frontends use **npm** — don't mix them
- Ruff handles both linting and formatting — do not add separate formatters
- The project uses a monorepo structure but each frontend has independent dependencies
- Docker Compose is for local dev; frontends use multi-stage builds for production images
