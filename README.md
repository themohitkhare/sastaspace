# SastaSpace

A portfolio of interactive projects — multiplayer board games, AI solvers, and RPG builders — served from a single FastAPI backend through a Traefik reverse proxy.

## Tech Stack

- **Backend**: FastAPI + MongoDB (Python 3.11+, uv)
- **Frontends**: React 18 + Vite + Tailwind CSS (brutalist design system)
- **Reverse Proxy**: Traefik v2.11 (routes all sub-apps through localhost:80)
- **Containerization**: Docker + Docker Compose (multi-stage builds)
- **Testing**: pytest (backend), Vitest + Testing Library (frontend), Playwright (E2E)
- **Observability**: Grafana + Loki + Promtail

## Projects

| Project | URL | Description |
|---------|-----|-------------|
| **SastaDice** | `/sastadice/` | Multiplayer board game with auctions, trading, and dynamic economy |
| **SastaHero** | `/sastahero/` | Interactive RPG character builder — pick a class, allocate stats, export as PNG |
| **Sudoku** | `/sudoku/` | Player vs Genetic Algorithm — upload puzzles via OCR or play manually |

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
| Sudoku | http://localhost/sudoku/ |
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
│   │   │   ├── sastahero/     # Hero builder API
│   │   │   └── sudoku/        # Genetic algorithm solver
│   │   ├── core/              # Config, logging
│   │   └── db/                # MongoDB session
│   └── tests/                 # pytest test suite
├── frontends/
│   ├── shared/                # Shared React components (Navbar, assets)
│   ├── sastaspace/            # Landing page (React/Vite)
│   ├── sastadice/             # Board game frontend (React/Vite)
│   ├── sastahero/             # Hero builder frontend (React/Vite)
│   └── sudoku/                # Sudoku frontend (React/Vite)
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
cd frontends/sudoku   # or sastadice, sastahero, sastaspace
npm install
npm run dev
```

### Running Tests

```bash
# All tests (backend + all frontends)
make test-full

# Backend only
make test-backend

# Specific frontend
make test-frontend-sudoku
make test-frontend-sastahero
make test-frontend-sastadice

# Full quality audit (lint + typecheck + complexity + coverage)
make audit
```

## API Endpoints

- `GET /api/v1/common/health` — Health check + MongoDB connectivity
- `GET /api/v1/sastahero/classes` — All hero class definitions
- `POST /api/v1/sastahero/generate` — Random hero with weighted stat allocation
- `GET /api/v1/sudoku/matches/{id}` — Get match state
- `POST /api/v1/sastadice/games` — Create a new game
