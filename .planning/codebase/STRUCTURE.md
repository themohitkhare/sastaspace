# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
sastaspace/                  # project root
├── sastaspace/              # main Python package
│   ├── __init__.py          # empty marker
│   ├── cli.py               # Click CLI entrypoint and pipeline orchestration
│   ├── config.py            # pydantic-settings Settings class
│   ├── crawler.py           # Playwright-based web crawler + CrawlResult dataclass
│   ├── deployer.py          # Filesystem deploy + registry management
│   ├── redesigner.py        # Claude AI integration and HTML validation
│   └── server.py            # FastAPI preview server + ensure_running()
├── tests/                   # pytest test suite (mirrors package structure)
│   ├── __init__.py          # empty marker
│   ├── test_cli.py          # CLI command tests
│   ├── test_config.py       # Settings tests
│   ├── test_crawler.py      # CrawlResult and crawl() tests
│   ├── test_deployer.py     # deploy(), derive_subdomain(), registry tests
│   ├── test_redesigner.py   # redesign() and HTML validation tests
│   └── test_server.py       # FastAPI routes and ensure_running() tests
├── sites/                   # runtime output directory (gitignored)
│   ├── _registry.json       # JSON array of deployed site metadata
│   ├── .server_port         # active server port written by ensure_running()
│   ├── .server.log          # uvicorn subprocess stdout/stderr
│   └── {subdomain}/         # one directory per deployed redesign
│       ├── index.html       # AI-generated single-file redesign
│       └── metadata.json    # {subdomain, original_url, timestamp, status}
├── docs/                    # project documentation
├── .planning/               # GSD planning workspace
│   └── codebase/            # codebase analysis documents
├── pyproject.toml           # project metadata, dependencies, ruff/pytest config
├── Makefile                 # install / lint / test / ci targets
├── uv.lock                  # uv lockfile
└── README.md                # project readme
```

## Directory Purposes

**`sastaspace/` (package):**
- Purpose: All application source code
- Contains: One module per responsibility — CLI, config, crawler, deployer, redesigner, server
- Key files: `cli.py` (orchestration), `crawler.py` (data model), `redesigner.py` (AI integration)

**`tests/`:**
- Purpose: pytest test suite
- Contains: One test file per source module, named `test_{module}.py`
- Key files: `test_redesigner.py` (AI output handling), `test_deployer.py` (filesystem logic)

**`sites/`:**
- Purpose: Runtime output — stores all deployed HTML redesigns and the server state files
- Contains: `_registry.json`, `.server_port`, `.server.log`, and one subdirectory per deployed site
- Generated: Yes (created at runtime by `deploy()` and `ensure_running()`)
- Committed: No (gitignored)

**`docs/`:**
- Purpose: Project documentation
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning workflow artifacts
- Contains: `codebase/` analysis documents, planning files
- Generated: Yes (by GSD commands)
- Committed: Yes

## Key File Locations

**Entry Points:**
- `sastaspace/cli.py`: CLI `main()` group — registered as `sastaspace` script in `pyproject.toml`
- `sastaspace/server.py`: Module-level `app` FastAPI instance — used by uvicorn subprocess

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, ruff line-length/targets, pytest asyncio_mode
- `sastaspace/config.py`: `Settings` class — reads `.env` for `claude_code_api_url`, `sites_dir`, `server_port`, `claude_model`
- `.env` (not committed): Must define `ANTHROPIC_API_KEY` for the claude-code-api gateway

**Core Logic:**
- `sastaspace/crawler.py`: `CrawlResult` dataclass + `crawl()` async function
- `sastaspace/redesigner.py`: `redesign()` function, `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`
- `sastaspace/deployer.py`: `deploy()`, `derive_subdomain()`, `load_registry()`, `save_registry()`

**Testing:**
- `tests/test_crawler.py`: Unit tests for `CrawlResult` and `crawl()` with mocked Playwright
- `tests/test_redesigner.py`: Unit tests for HTML cleaning, validation, and OpenAI client calls
- `tests/test_server.py`: FastAPI `TestClient` tests plus `ensure_running()` subprocess tests

## Naming Conventions

**Files:**
- Package modules: `snake_case.py` matching their primary responsibility (`crawler.py`, `deployer.py`)
- Test files: `test_{module_name}.py` co-located in `tests/` (not alongside source)

**Directories:**
- `sites/{subdomain}`: kebab-case slug derived from original hostname (`acme-com`, `acme-corp-co-uk`)
- Collision suffixes: `{subdomain}--2`, `{subdomain}--3` (double hyphen to avoid ambiguity)

**Python symbols:**
- Public functions: `snake_case` (`crawl`, `redesign`, `deploy`, `ensure_running`)
- Private helpers: `_snake_case` prefix (`_clean_html`, `_validate_html`, `_extract_text`, `_ensure_chromium`, `_load_config`)
- Dataclasses: `PascalCase` (`CrawlResult`, `DeployResult`)
- Exceptions: `PascalCase` with `Error` suffix (`RedesignError`)
- Settings class: `Settings`
- Constants/prompts: `UPPER_SNAKE_CASE` (`SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`)

## Where to Add New Code

**New pipeline stage (e.g., post-processing, optimisation):**
- Implementation: `sastaspace/{stage_name}.py` — expose one public function
- Tests: `tests/test_{stage_name}.py`
- Wire-up: Add call in the `redesign_cmd` function in `sastaspace/cli.py`

**New CLI command:**
- Implementation: New `@main.command(...)` function in `sastaspace/cli.py`
- Tests: `tests/test_cli.py`

**New configuration setting:**
- Add field with default to `Settings` in `sastaspace/config.py`
- Document env var name (pydantic-settings derives it from the field name, uppercased)

**New FastAPI route:**
- Add `@app.get(...)` inside `make_app()` in `sastaspace/server.py`
- Tests: `tests/test_server.py` using `make_test_client(sites_dir)`

**Utilities / shared helpers:**
- Currently no shared utilities module. Add `sastaspace/utils.py` if cross-module helpers are needed.

## Special Directories

**`sites/`:**
- Purpose: All runtime output — HTML files, metadata, server state
- Generated: Yes (by application at runtime)
- Committed: No

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents for GSD workflow
- Generated: Yes (by `/gsd:map-codebase`)
- Committed: Yes

---

*Structure analysis: 2026-03-21*
