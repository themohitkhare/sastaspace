# SastaSpace Monorepo

A monorepo containing a FastAPI backend with DuckDB and multiple frontend projects.

## Project Structure

```
sastaspace/
├── backend/               # FastAPI backend with DuckDB
│   ├── app/
│   │   ├── main.py        # Entry point
│   │   ├── core/          # Config, Security, Logging
│   │   ├── db/            # DuckDB connection & Schema management
│   │   └── api/           # API Routes
│   └── data/              # DuckDB data files (Git-ignored)
│
├── frontends/             # Frontend projects
│   ├── main_website/      # sastaspace.com (Landing page)
│   ├── sastahero/         # sastahero.sastaspace.com
│   └── sasta/             # sasta.sastaspace.com
│
└── shared/                # Shared code between frontends
```

## Quick Start

### Development

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run backend locally:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

3. **Run with Docker:**
   ```bash
   docker-compose up -d
   ```

## Architecture

- **Backend:** FastAPI (Python 3.11+), DuckDB (Embedded OLAP DB), Pydantic V2
- **Frontend:** HTML/HTMX + Tailwind (primary), React (secondary/optional)
- **Infrastructure:** Docker Compose, Traefik (Reverse Proxy for subdomains)

## Subdomain Strategy

- `sastaspace.com` -> Main frontend
- `*.sastaspace.com` -> Routed to specific project containers via Traefik
