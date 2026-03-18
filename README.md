# SastaSpace

A portfolio of interactive projects — multiplayer board games and RPG builders — served from a single FastAPI backend through a Traefik reverse proxy.

## Tech Stack

- **Backend**: FastAPI + MongoDB + Redis (Python 3.11+, uv)
- **Frontends**: React 18 + Vite + Tailwind CSS (brutalist design system)
- **Worker Framework**: Redis Streams consumer groups (BaseWorker pattern)
- **Reverse Proxy**: Traefik v2.11 (routes all sub-apps through localhost:80)
- **Containerization**: Docker + Docker Compose (multi-stage builds)
- **Testing**: pytest (backend), Vitest + Testing Library (frontend), Playwright (E2E)
- **Observability**: Grafana + Loki + Promtail

## Projects

| Project | URL | Description |
|---------|-----|-------------|
| **SastaDice** | `/sastadice/` | Multiplayer board game with auctions, trading, and dynamic economy |
| **SastaHero** | `/sastahero/` | Interactive RPG character builder — pick a class, allocate stats, export as PNG |

## Quick Start

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Access

| Service | URL |
|---------|-----|
| Landing Page | http://localhost/ |
| SastaDice | http://localhost/sastadice/ |
| SastaHero | http://localhost/sastahero/ |
| Backend API | http://localhost/api/v1/ |
| API Docs | http://localhost:8000/docs |
| Traefik Dashboard | http://localhost:8080 |
| Grafana (Logs) | http://localhost:3000 |

## Project Structure

```
sastaspace/
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # API router
│   │   ├── modules/
│   │   │   ├── common/        # Health checks
│   │   │   ├── sastadice/     # Board game logic
│   │   │   └── sastahero/     # Hero builder API
│   │   ├── worker/            # Redis Streams worker framework
│   │   │   ├── base.py        # BaseWorker (generic consumer)
│   │   │   ├── mutation_worker.py
│   │   │   └── solver_coordinator.py
│   │   ├── core/              # Config, logging, Redis
│   │   └── db/                # MongoDB session
│   └── tests/                 # pytest test suite
├── frontends/
│   ├── shared/                # Shared React components (Navbar, assets)
│   ├── sastaspace/            # Landing page (React/Vite)
│   ├── sastadice/             # Board game frontend (React/Vite)
│   └── sastahero/             # Hero builder frontend (React/Vite)
├── grafana/                   # Grafana provisioning
├── loki/                      # Loki log aggregation config
├── promtail/                  # Log collection config
├── scripts/                   # Developer utilities
└── docker-compose.yml
```

## Development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### Frontend (any sub-app)

```bash
cd frontends/sastadice   # or sastahero, sastaspace
npm install
npm run dev
```

### Running Tests

```bash
# All tests (backend + all frontends)
make test-full

# Parallel CI (~7s)
make ci-fast

# Backend only
make test-backend

# Specific frontend
make test-frontend-sastahero
make test-frontend-sastadice

# Full quality audit (lint + typecheck + complexity + coverage)
make audit
```

## Worker Framework

The backend includes a reusable Redis Streams worker framework (`app/worker/`). Same Docker image runs different roles via `APP_MODE` env var:

| `APP_MODE` | What it runs |
|------------|-------------|
| `SERVER` | FastAPI HTTP server (default) |
| `CONSUMER` | Redis Streams consumer (MutationWorker) |
| `COORDINATOR` | Task orchestrator (SolverCoordinator) |
| `JOB` | One-shot job |
| `CRONJOB` | Periodic tasks |

## API Endpoints

- `GET /api/v1/common/health` — Health check + MongoDB connectivity
- `GET /api/v1/sastahero/classes` — All hero class definitions
- `POST /api/v1/sastahero/generate` — Random hero with weighted stat allocation
- `POST /api/v1/sastadice/games` — Create a new game
