# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Linear Pipeline with CLI Orchestration

**Key Characteristics:**
- Five single-responsibility modules wired together by the CLI
- Each module exposes one public function or dataclass (crawl, redesign, deploy, ensure_running, Settings)
- No dependency injection framework — dependencies are passed as plain function arguments
- Async only at the crawl boundary; all other modules are synchronous

## Layers

**CLI (Orchestration):**
- Purpose: Parses user commands, sequences the pipeline, and renders terminal output
- Location: `sastaspace/cli.py`
- Contains: Click command group (`main`), five commands (`redesign`, `list`, `open`, `remove`, `serve`)
- Depends on: `crawler`, `redesigner`, `deployer`, `server`, `config`
- Used by: End users via `sastaspace` entrypoint defined in `pyproject.toml`

**Config:**
- Purpose: Centralises all environment-driven settings with defaults
- Location: `sastaspace/config.py`
- Contains: Single `Settings` class (pydantic-settings `BaseSettings`)
- Depends on: Nothing internal
- Used by: `cli.py` via lazy `_load_config()` call inside each command

**Crawler:**
- Purpose: Fetches a remote URL using a headless browser and extracts structured page data
- Location: `sastaspace/crawler.py`
- Contains: `CrawlResult` dataclass, `crawl()` async function, private HTML extraction helpers
- Depends on: Playwright, BeautifulSoup4
- Used by: `cli.py` (`redesign` command)

**Redesigner:**
- Purpose: Calls the Claude AI gateway with crawl data and returns a single-file HTML redesign
- Location: `sastaspace/redesigner.py`
- Contains: `redesign()` function, `RedesignError` exception, prompt constants, `_clean_html()`, `_validate_html()`
- Depends on: `crawler.CrawlResult`, OpenAI SDK (pointed at claude-code-api gateway)
- Used by: `cli.py` (`redesign` command)

**Deployer:**
- Purpose: Persists redesigned HTML to the filesystem and maintains a JSON registry
- Location: `sastaspace/deployer.py`
- Contains: `DeployResult` dataclass, `deploy()`, `derive_subdomain()`, `load_registry()`, `save_registry()`
- Depends on: stdlib only (pathlib, json, re, os, datetime)
- Used by: `cli.py` (`redesign`, `list`, `remove` commands)

**Server:**
- Purpose: Serves the local sites directory over HTTP for browser preview
- Location: `sastaspace/server.py`
- Contains: `make_app()` factory, module-level `app` instance, `ensure_running()` subprocess manager
- Depends on: FastAPI, uvicorn (spawned as subprocess)
- Used by: `cli.py` (`redesign`, `open`, `serve` commands); spawned by `ensure_running()`

## Data Flow

**Primary `redesign` command pipeline:**

1. User runs `sastaspace redesign <url>`
2. `cli.py` calls `asyncio.run(crawl(url))` → returns `CrawlResult` with page title, HTML source, screenshot (base64 PNG), headings, links, colors, fonts, sections
3. `CrawlResult.to_prompt_context()` serialises the crawl data into a markdown prompt string
4. `cli.py` calls `redesign(crawl_result, api_url, model)` → sends system prompt + user text + screenshot image to Claude via OpenAI-compatible API → returns validated HTML string
5. `cli.py` calls `deploy(url, html, sites_dir)` → writes `sites/{subdomain}/index.html` and `metadata.json`, appends to `sites/_registry.json` → returns `DeployResult`
6. `cli.py` calls `ensure_running(sites_dir)` → checks if uvicorn is listening, spawns detached subprocess if not, returns port number
7. Browser opens `http://localhost:{port}/{subdomain}/`

**Error Propagation:**
- `crawl()` never raises; it sets `CrawlResult.error` on failure
- `cli.py` checks `crawl_result.error` before continuing and exits with `SystemExit(1)`
- `redesign()` raises `RedesignError` for invalid/truncated AI output or failed crawl input
- `deploy()` raises filesystem exceptions directly (not caught — treated as unexpected)

## Key Abstractions

**CrawlResult:**
- Purpose: Carries all data extracted from a crawled page, including a base64 screenshot for the multimodal AI call
- Location: `sastaspace/crawler.py`
- Pattern: Python `@dataclass` with `error: str = ""` sentinel field; `to_prompt_context()` method serialises fields into a markdown prompt

**DeployResult:**
- Purpose: Communicates the outcome of a deploy operation back to the CLI
- Location: `sastaspace/deployer.py`
- Pattern: Plain `@dataclass` — no methods

**RedesignError:**
- Purpose: Distinguishes AI output validation failures from unexpected exceptions
- Location: `sastaspace/redesigner.py`
- Pattern: Bare `Exception` subclass; caught explicitly in `cli.py`

**Settings:**
- Purpose: Single source of truth for runtime configuration
- Location: `sastaspace/config.py`
- Pattern: pydantic-settings `BaseSettings`; reads `.env` file; all fields have defaults

## Entry Points

**CLI entrypoint:**
- Location: `sastaspace/cli.py` — `main()` Click group
- Triggers: `sastaspace` command installed via `[project.scripts]` in `pyproject.toml`
- Responsibilities: Sequences pipeline, displays Rich progress/panels, handles errors

**ASGI app entrypoint:**
- Location: `sastaspace/server.py` — module-level `app` object (created by `make_app()`)
- Triggers: uvicorn subprocess spawned by `ensure_running()` or `serve` CLI command
- Responsibilities: Serves `sites/` directory over HTTP; reads `SASTASPACE_SITES_DIR` env var to find sites root

**Package install:**
- Location: `pyproject.toml` `[project.scripts]` → `sastaspace.cli:main`
- Dev runner: `uv run pytest tests/ -v` (see `Makefile`)

## Error Handling

**Strategy:** Error-as-value at the crawl boundary; exceptions everywhere else

**Patterns:**
- `CrawlResult.error` is set to the exception message string when crawl fails; caller checks before proceeding
- `RedesignError` is raised for predictable AI output failures (empty, missing DOCTYPE, truncated)
- Generic `Exception` from the OpenAI client is caught separately in `cli.py` with a distinct user message
- `deploy()` uses atomic write-then-rename (`os.replace`) to avoid corrupt registry files
- `ensure_running()` uses a polling loop (max 5 seconds) to confirm subprocess is listening before returning

## Cross-Cutting Concerns

**Logging:** No structured logging. `cli.py` uses Rich console for user-facing output. `server.py` appends uvicorn stdout/stderr to `sites/.server.log` when running as a detached subprocess.

**Validation:** HTML output from the AI is validated in `sastaspace/redesigner.py` (`_validate_html`) — checks for non-empty output, `<!DOCTYPE html>`, and closing `</html>` tag.

**Authentication:** The OpenAI client in `redesigner.py` is instantiated with `api_key="claude-code"` (literal string). Real auth is handled by the external claude-code-api gateway, which expects `ANTHROPIC_API_KEY` in the environment.

---

*Architecture analysis: 2026-03-21*
