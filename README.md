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

## Running Backend as a Systemd Service (Non-Docker)

To run the backend service in the background using systemd (instead of Docker):

### Installation

```bash
# Install the systemd service
make service-install

# Enable service to start on boot (optional)
sudo systemctl enable sastaspace-backend

# Start the service
make service-start
```

### Service Management

```bash
# Check service status
make service-status

# View logs (follow mode)
make service-logs

# Stop the service
make service-stop

# Remove the service
make service-remove
```

The service will automatically restart if it crashes and will start on system boot if enabled.

## DuckDB CLI Access

DuckDB is already installed and available via the Python package. You can also access DuckDB CLI directly:

### Using DuckDB CLI

```bash
# Access DuckDB CLI with project database
make duckdb-cli

# Or directly
./backend/scripts/duckdb-cli.sh

# Or use DuckDB CLI directly (without sudo)
duckdb backend/data/sastaspace.db
```

**Note:** Don't use `sudo duckdb` - DuckDB CLI is installed in your user's local bin (`~/.local/bin/duckdb`), not in system paths accessible by sudo.

### DuckDB Web UI

If you want to use the DuckDB web UI:

```bash
duckdb -ui backend/data/sastaspace.db
```

This will start a local web server (usually on http://localhost:8080) for visual database interaction.

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
