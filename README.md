# SastaSpace

A multi-frontend, FastAPI backend application with Traefik reverse proxy.

## Architecture

- **Backend**: FastAPI with DuckDB (Python 3.11)
- **Frontends**: 
  - `sastaspace.com` - Main frontend (React/Vite)
  - `sastahero.sastaspace.com` - SastaHero frontend
  - `sasta.sastaspace.com` - Sasta frontend
- **Reverse Proxy**: Traefik v2.11
- **API**: `api.sastaspace.com`

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 80, 443, and 8080 available

### Start Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Access Services

- **Traefik Dashboard**: http://localhost:8080
- **Backend API**: http://localhost/api/v1/ (or http://api.sastaspace.com if DNS configured)
- **Main Frontend**: http://localhost/ (or http://sastaspace.com if DNS configured)
- **Health Check**: http://localhost/api/v1/common/health

### Development

#### Backend Development

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

#### Frontend Development

The main frontend (sastaspace) uses Vite. For development:

```bash
cd frontends/sastaspace
npm install
npm run dev
```

## Environment Variables

Create a `.env` file in the root directory:

```env
ACME_EMAIL=admin@sastaspace.com
DB_PATH=/app/data/sastaspace.db
```

## Project Structure

```
sastaspace/
├── backend/           # FastAPI backend
│   ├── app/          # Application code
│   ├── data/         # DuckDB database files
│   └── Dockerfile    # Backend container
├── frontends/        # Frontend applications
│   ├── sastaspace/   # Main React frontend
│   ├── sastahero/    # SastaHero frontend
│   └── sasta/        # Sasta frontend
├── traefik/          # Traefik configuration
└── docker-compose.yml
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /api/v1/common/health` - Health check with database connectivity

## Troubleshooting

### Check service status
```bash
docker-compose ps
```

### View logs
```bash
docker-compose logs [service-name]
```

### Rebuild after changes
```bash
docker-compose up -d --build
```

### Database location
The DuckDB database is stored in `backend/data/sastaspace.db` and is persisted via Docker volumes.
