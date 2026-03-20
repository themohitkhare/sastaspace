# Coding Conventions

**Analysis Date:** 2026-03-21

## Naming Patterns

**Files:**
- `snake_case.py` for all source modules: `crawler.py`, `redesigner.py`, `deployer.py`
- `test_{module}.py` naming mirrors source: `test_crawler.py` mirrors `crawler.py`

**Functions:**
- `snake_case` for all functions and methods
- Private helpers prefixed with `_`: `_ensure_chromium()`, `_clean_html()`, `_validate_html()`, `_extract_text()`, `_extract_headings()`, `_unique_subdomain()`, `_is_port_listening()`
- Public API functions are un-prefixed: `crawl()`, `redesign()`, `deploy()`, `load_registry()`, `save_registry()`
- CLI command functions use `_cmd` suffix to avoid name clashes with imported functions: `redesign_cmd`, `list_cmd`, `open_cmd`, `remove_cmd`, `serve_cmd`

**Variables:**
- `snake_case` throughout
- Descriptive names: `crawl_result`, `sites_dir`, `port_file`, `registry_path`
- Loop variables kept short and contextual: `sub`, `orig`, `ts`, `entry`, `e`

**Classes:**
- `PascalCase`: `CrawlResult`, `DeployResult`, `RedesignError`, `Settings`
- Dataclasses used for plain data containers; no base classes besides `@dataclass`
- Custom exceptions inherit from `Exception` directly with a docstring

**Constants / module-level:**
- `UPPER_SNAKE_CASE` for string constants: `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`, `SAMPLE_HTML` (in tests)
- Module-level singletons use underscore prefix: `_SITES_DIR`, `_default_sites_dir`

## Code Style

**Formatter:**
- `ruff format` (Black-compatible)
- Line length: 100 characters (set in `pyproject.toml` `[tool.ruff]`)

**Linter:**
- `ruff check` with rule sets: `E` (pycodestyle), `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- Target version: `py311`
- No `# noqa` suppressions or `type: ignore` comments anywhere in the codebase

**Type Annotations:**
- All public function signatures are fully annotated with return types
- `from __future__ import annotations` used in `crawler.py`, `cli.py`, `server.py`, `deployer.py`, `redesigner.py` — enables PEP 563 postponed evaluation
- Modern union syntax used: `str | None` (not `Optional[str]`)
- `list[str]`, `list[dict]` used (not `List[str]` from `typing`)

## Import Organization

**Order (enforced by ruff `I`):**
1. `from __future__ import annotations` (always first when present)
2. Standard library (`asyncio`, `json`, `pathlib`, `re`, `subprocess`, etc.)
3. Third-party packages (`bs4`, `click`, `fastapi`, `openai`, `playwright`, `rich`)
4. Local package imports (`from sastaspace.crawler import ...`)

**Style:**
- Absolute imports only: `from sastaspace.crawler import CrawlResult`
- No wildcard imports
- One deferred import used in `cli.py` inside a function body for import-cycle avoidance: `from sastaspace.config import Settings` inside `_load_config()`

## Error Handling

**Patterns:**
- Errors that indicate bad data or invalid AI output raise a typed custom exception: `RedesignError` from `sastaspace/redesigner.py`
- Broad `except Exception` used only at module boundaries to catch all unexpected failures and store the error on a result object (e.g., `crawl()` sets `CrawlResult.error = str(exc)` rather than propagating)
- Narrow `except (json.JSONDecodeError, OSError)` catches used for recoverable I/O failures in `load_registry()` and `server.py`
- CLI layer catches specific exceptions (`RedesignError`, generic `Exception`) and calls `raise SystemExit(1)` after printing a Rich Panel error message
- No bare `except:` clauses; `except Exception:` is the widest form used
- `_validate_html()` in `redesigner.py` raises `RedesignError` with descriptive messages for empty response, missing doctype, or truncated output

**Error propagation model:**
- Functions return result objects with `.error` field set (not raised) for expected failures: `CrawlResult.error`
- Functions raise typed exceptions for programming errors or invalid inputs: `RedesignError`
- CLI is the only place that converts exceptions to user-facing output and exit codes

## Logging

**Framework:** None — no logging module used

**Patterns:**
- All user-facing output goes through `rich.console.Console` (module-level `console = Console()` in `cli.py`)
- Rich `Panel` used for error messages; `Table` for listing; `Progress` with `SpinnerColumn` for long operations
- Internal functions are silent (no print statements, no logging calls)
- Server startup messages written to `sites_dir/.server.log` via subprocess stdout redirect

## Comments

**When to Comment:**
- Module-level comment on first line giving the module name: `# sastaspace/crawler.py`
- Docstrings on all public functions — concise single-line format for simple cases, multi-line with `Raises:` section when exceptions are documented
- Private helpers get a brief docstring explaining what they do, not how
- No inline comments used; code is written to be self-explanatory

**Docstring style:**
```python
def derive_subdomain(url: str) -> str:
    """
    Derive a filesystem-safe subdomain slug from a URL.

    https://www.acme-corp.co.uk/shop -> acme-corp-co-uk
    """
```
```python
def redesign(...) -> str:
    """
    Use the claude-code-api gateway to redesign a crawled website into a single HTML file.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
```

## Function Design

**Size:** Functions are small and single-purpose; largest is `crawl()` at ~90 lines due to Playwright async context management

**Parameters:**
- Keyword arguments with defaults for optional params: `subdomain: str | None = None`
- `Path` objects used for filesystem parameters, not raw strings
- Config injected at call sites from `Settings`; functions do not read `Settings` directly

**Return Values:**
- Dataclasses for structured results: `CrawlResult`, `DeployResult`
- `str` for HTML output from `redesign()`
- `list[dict]` for registry data
- `int` for port numbers from `ensure_running()`

## Module Design

**Exports:**
- No `__all__` defined in any module; public API is implicit (non-underscore names)
- `sastaspace/__init__.py` is empty — no re-exports

**Factory functions:**
- `make_app(sites_dir: Path) -> FastAPI` in `server.py` creates a configured app instance, enabling testability
- Module-level `app = make_app(...)` at bottom of `server.py` provides the default uvicorn entry point

**Dataclasses:**
- `@dataclass` used (not Pydantic models) for `CrawlResult` and `DeployResult`
- `field(default_factory=list)` used for mutable defaults in `CrawlResult`
- `Settings` uses `pydantic_settings.BaseSettings` for environment-driven config only

---

*Convention analysis: 2026-03-21*
