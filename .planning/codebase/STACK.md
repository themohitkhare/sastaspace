# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- Python 3.11+ - All application code (`sastaspace/`, `tests/`)

**Secondary:**
- HTML/CSS/JavaScript - Generated output only (AI-produced redesigned site files written to `sites/`)

## Runtime

**Environment:**
- Python >=3.11 (declared in `pyproject.toml`); runtime cache confirms CPython 3.14 in use locally

**Package Manager:**
- `uv` — sync via `uv sync`, scripts run via `uv run`
- Lockfile: `uv.lock` present and committed

## Frameworks

**Core:**
- FastAPI 0.135.1 — local preview HTTP server (`sastaspace/server.py`)
- Uvicorn 0.42.0 — ASGI server; used both as programmatic subprocess and foreground dev runner

**CLI:**
- Click 8.3.1 — CLI command group with subcommands (`sastaspace/cli.py`)
- Rich 14.3.3 — terminal output, spinners, panels, tables (`sastaspace/cli.py`)

**Web Crawling:**
- Playwright 1.58.0 — headless Chromium crawling (`sastaspace/crawler.py`); Chromium browser auto-installed via `playwright install chromium`
- BeautifulSoup4 4.14.3 — HTML parsing for content extraction (`sastaspace/crawler.py`)

**AI Client:**
- openai 2.29.0 — OpenAI-compatible client pointed at local claude-code-api gateway (`sastaspace/redesigner.py`)

**Configuration:**
- pydantic-settings 2.13.1 — `Settings` class with `.env` file support (`sastaspace/config.py`)
- python-dotenv 1.2.2 — `.env` file loading (transitive via pydantic-settings)

**Testing:**
- pytest 9.0.2 — test runner (`tests/`)
- pytest-asyncio 1.3.0 — async test support; configured with `asyncio_mode = "auto"` in `pyproject.toml`

**Build:**
- hatchling — build backend declared in `pyproject.toml`

**Linting/Formatting:**
- ruff 0.15.7 — linter and formatter; config in `pyproject.toml` (`line-length = 100`, `target-version = "py311"`, rules `E, F, I, UP`)

## Key Dependencies

**Critical:**
- `openai` 2.29.0 — all AI redesign requests go through this client; pointed at `claude_code_api_url` (not the OpenAI API directly). Changing this breaks the redesign pipeline.
- `playwright` 1.58.0 — headless browser required for crawling. Chromium binary must be installed separately (`playwright install chromium`).
- `fastapi` + `uvicorn` — the entire local preview and serving layer.

**Infrastructure:**
- `pydantic-settings` 2.13.1 — typed config management; all settings flow through `sastaspace/config.py`
- `beautifulsoup4` 4.14.3 — HTML parsing in crawler
- `rich` 14.3.3 — all CLI user-facing output

## Configuration

**Environment:**
- Configuration is managed via `sastaspace/config.py` using `pydantic-settings`
- `.env` file is loaded automatically when present (see `.env.example`)
- Key settings:
  - `CLAUDE_CODE_API_URL` — base URL of local claude-code-api gateway (default: `http://localhost:8000/v1`)
  - `SITES_DIR` — directory for saved redesigns (default: `./sites`)
  - `SERVER_PORT` — preview server port (default: `8080`)
  - `CLAUDE_MODEL` — model string passed to API (default: `claude-sonnet-4-5-20250929`)
- `ANTHROPIC_API_KEY` is referenced in `.env.example` but consumed by the external claude-code-api gateway, not directly by this application

**Build:**
- `pyproject.toml` — single source of truth for project metadata, dependencies, scripts, ruff config, pytest config
- No `setup.py` or `setup.cfg`; hatchling build backend

## Platform Requirements

**Development:**
- Python 3.11+
- `uv` package manager
- Chromium browser (installed via `uv run playwright install chromium`)
- Running claude-code-api gateway on `localhost:8000` for redesigns

**Production:**
- Local-only tool; no cloud deployment target. FastAPI server binds to `127.0.0.1` only.
- Generated sites saved to local filesystem under `sites/`

---

*Stack analysis: 2026-03-21*
