# Codebase Concerns

**Analysis Date:** 2026-03-21

## Tech Debt

**Hardcoded API key placeholder in redesigner:**
- Issue: `api_key="claude-code"` is hardcoded as a string literal in `redesigner.py`. This is a dummy value used to satisfy the OpenAI client constructor when routing through the local claude-code-api gateway, but it makes the code brittle — if the gateway ever enforces auth, this breaks silently with a misleading error.
- Files: `sastaspace/redesigner.py:92`
- Impact: Any future real-key auth requirement causes a non-obvious failure; the error message in `cli.py` says "Check your ANTHROPIC_API_KEY in .env" but the key is never read from config for this code path.
- Fix approach: Thread the actual API key from `Settings` through `cli.py` → `redesigner.redesign()` as a parameter, rather than using a hardcoded placeholder.

**Default parameter mirrors config default, not config value:**
- Issue: `redesign()` has `api_url: str = "http://localhost:8000/v1"` as a default parameter. This duplicates the default already in `Settings.claude_code_api_url`, creating two places that must stay in sync.
- Files: `sastaspace/redesigner.py:80-81`, `sastaspace/config.py:10`
- Impact: If the default URL is changed in `Settings`, callers using the default parameter continue pointing at the old URL.
- Fix approach: Remove the default from `redesign()`'s signature; make it a required parameter. `cli.py` already passes `cfg.claude_code_api_url` explicitly.

**`CLAUDE_MODEL` env var name mismatch between README and Settings:**
- Issue: `README.md:45` documents the env var as `CLAUDE_MODEL` with default `claude-sonnet-4-20250514`. `Settings` in `config.py:13` uses field name `claude_model` (resolves to `CLAUDE_MODEL`) with default `claude-sonnet-4-5-20250929`. `.env.example:7` also shows `claude-sonnet-4-20250514`. The model names are inconsistent across all three files.
- Files: `sastaspace/config.py:13`, `.env.example:7`, `README.md:45`
- Impact: Users following the README or `.env.example` configure a model name that doesn't match what the code defaults to, causing confusion about which model actually runs.
- Fix approach: Align all three to the same model string.

**`_ensure_chromium` silently swallows all failures:**
- Issue: The entire body of `_ensure_chromium()` is wrapped in a bare `except Exception: pass`. If Playwright binary installation fails for any reason (network, permissions, disk space), the function returns silently. The `crawl()` call that follows immediately fails with a cryptic browser-not-found error rather than a clear installation error.
- Files: `sastaspace/crawler.py:15-29`
- Impact: Debugging first-time setup failures is unnecessarily difficult.
- Fix approach: Log a warning or re-raise with a descriptive message when the subprocess returns a non-zero exit code.

**`--reload` flag in production `serve` command:**
- Issue: `cli.py:201` passes `--reload` to uvicorn when the user runs `sastaspace serve`. The `--reload` flag is a development convenience that watches for file changes and restarts the server. It should not be the default for a user-facing production serve command.
- Files: `sastaspace/cli.py:199-203`
- Impact: Unnecessary file-watching overhead; unexpected server restarts if any file in the project directory changes while serving.
- Fix approach: Remove `--reload` from the serve command, or add a `--dev` flag to enable it explicitly.

**Relative `sites_dir` default in `cli.py` ignores config:**
- Issue: `cli.py:24` defines `DEFAULT_SITES_DIR = Path("./sites")` as a module-level constant. If the user runs `sastaspace` from a directory other than the project root, this resolves to the wrong path. The `Settings.sites_dir` config field exists but is only used to pass the port and model — `sites_dir` itself is taken from the CLI constant, not from `Settings`, unless the user passes `--sites-dir`.
- Files: `sastaspace/cli.py:24`, `sastaspace/config.py:11`
- Impact: Silent data inconsistency — sites are written and read from different directories depending on working directory.
- Fix approach: Fall back to `Settings().sites_dir` when `--sites-dir` is not provided, rather than the hardcoded `./sites` constant.

## Security Considerations

**Path traversal in server asset route:**
- Risk: `server.py:93` constructs `asset_path = sites_dir / subdomain / path` where both `subdomain` and `path` come directly from URL path parameters with no sanitization. A request to `GET /acme-com/../../_registry.json` would resolve to `sites_dir / "_registry.json"` and serve it (or any other file accessible to the server process).
- Files: `sastaspace/server.py:91-99`
- Current mitigation: None. FastAPI path parameters do not perform path canonicalization or sandbox checks.
- Recommendations: Resolve `asset_path` and verify it is within `sites_dir / subdomain` using `Path.resolve()` and `Path.is_relative_to()` before serving. Apply the same check to the `subdomain` segment itself.

**Subdomain path component not validated before filesystem access:**
- Risk: `server.py:83` and `server.py:93` use the `subdomain` URL segment directly in filesystem path operations without verifying it contains only safe characters. A `subdomain` containing `..` or null bytes could escape the `sites_dir` sandbox.
- Files: `sastaspace/server.py:82-89`
- Current mitigation: None.
- Recommendations: Validate `subdomain` against a strict allowlist regex (e.g., `^[a-z0-9][a-z0-9\-]{0,49}$`) matching `derive_subdomain()`'s output before any filesystem access.

**XSS via unsanitized `orig` URL in index page HTML:**
- Risk: `server.py:41-44` directly interpolates the `original_url` value from `_registry.json` into raw HTML without escaping: `f"<td><a href='{orig}' target='_blank'>{orig}</a></td>"`. If `original_url` contains `'` or HTML special characters (e.g., `javascript:alert(1)` or `' onclick='...`), they are rendered unescaped.
- Files: `sastaspace/server.py:33-44`
- Current mitigation: None.
- Recommendations: Use `html.escape()` on `orig`, `sub`, and `ts` before interpolating into the HTML template, or switch to a proper templating engine.

**Redesigned HTML served without sanitization:**
- Risk: The redesigned HTML output from the LLM is written to disk and served verbatim. A prompt injection attack (e.g., a crawled page that instructs the LLM to embed malicious JavaScript) would result in that script being served to any browser loading the preview.
- Files: `sastaspace/redesigner.py:112-123`, `sastaspace/server.py:88-89`
- Current mitigation: The system prompt instructs Claude not to add fake content, but this is not a security control.
- Recommendations: Consider adding a content security policy header when serving redesigned pages, or running HTML through a sanitizer that strips `<script>` tags.

## Performance Bottlenecks

**Hardcoded 2-second sleep in every crawl:**
- Problem: `crawler.py:162` unconditionally calls `await asyncio.sleep(2)` after `page.goto()` returns with `networkidle`. For fast sites this adds 2 seconds of dead time per redesign.
- Files: `sastaspace/crawler.py:162`
- Cause: Belt-and-suspenders wait for JS to settle after `networkidle` — a reasonable idea but implemented with a fixed sleep rather than a smarter condition.
- Improvement path: Replace with a configurable timeout or use `page.wait_for_function()` to detect stability dynamically.

**Screenshot captures only top 800px:**
- Problem: `crawler.py:166-168` limits the screenshot clip to `{"x":0,"y":0,"width":1280,"height":800}`. Long-form content pages (blogs, landing pages) are sent to the LLM with only the above-the-fold region, reducing redesign quality.
- Files: `sastaspace/crawler.py:166-168`
- Cause: Fixed viewport clip — no full-page screenshot option used.
- Improvement path: Use `full_page=True` on `page.screenshot()` or increase height to capture more content before passing to the LLM.

**`max_tokens=16000` may truncate large site redesigns:**
- Problem: `redesigner.py:119` sets `max_tokens=16000`. Complex sites with many sections can produce HTML well in excess of this, resulting in truncated output that fails `_validate_html()` with a "missing closing </html> tag" error, requiring the user to retry.
- Files: `sastaspace/redesigner.py:119`
- Cause: Static limit with no retry or streaming logic.
- Improvement path: Increase the limit (check model max), or implement a streaming + accumulation approach so truncation is detected earlier and the user is informed meaningfully.

## Fragile Areas

**`ensure_running()` has a race condition:**
- Files: `sastaspace/server.py:110-161`
- Why fragile: The function checks if a port is free, then starts a subprocess to bind it. Between the check and the bind, another process could occupy the port. The 5-second polling loop with `time.sleep(0.2)` will silently time out and return a port that the server is not actually listening on, causing the CLI to print a preview URL that returns a connection error.
- Safe modification: After the polling deadline, verify the port is actually listening before writing `.server_port` and returning; raise or warn if it is not.
- Test coverage: The test `test_ensure_running_spawns_subprocess_when_not_listening` mocks both `_is_port_listening` and `time.time` to avoid exercising this race.

**File handle leak in `ensure_running()`:**
- Files: `sastaspace/server.py:148`
- Why fragile: `stdout=open(log_file, "a")` opens a file handle and passes it to `subprocess.Popen` without storing a reference or closing it. On CPython this is usually collected by the GC, but it is technically a resource leak that can cause issues under load or in constrained environments.
- Safe modification: Open the file explicitly, store it, and close it after `Popen` returns (or use a context manager with `Popen`).
- Test coverage: Not tested; the test mocks `subprocess.Popen` entirely.

**`_ensure_chromium()` detection logic is inverted:**
- Files: `sastaspace/crawler.py:22-24`
- Why fragile: The install check runs `playwright install chromium --dry-run` and installs only when `result.returncode != 0 AND b"chromium" in result.stdout`. This condition is ambiguous: a non-zero return code from `--dry-run` does not reliably indicate that Chromium is missing. The actual Playwright CLI behavior for `--dry-run` varies by version.
- Safe modification: Use `playwright install chromium` unconditionally with a `--with-deps` flag, or check for the browser executable directly using `playwright._impl._driver.compute_driver_executable()`.
- Test coverage: `_ensure_chromium` is not tested at all — the crawler tests mock `async_playwright` at a higher level.

**`serve` command `--reload` starts server in the project working directory:**
- Files: `sastaspace/cli.py:191-204`
- Why fragile: Uvicorn's `--reload` mode watches the current working directory. Running `sastaspace serve` from different directories results in different watch roots, and the server module import path `sastaspace.server:app` only resolves if the package is on `sys.path`.
- Safe modification: Pass `--reload-dir` explicitly, or remove `--reload` as noted above.

## Missing Critical Features

**No input validation on the `url` argument:**
- Problem: The `redesign` CLI command accepts any string as `url` and passes it directly to `page.goto()`. Non-URL strings (e.g., bare hostnames, file paths, `javascript:` URIs) will cause cryptic errors from Playwright rather than a user-friendly validation message.
- Blocks: Clean error UX; security (prevents `file://` local filesystem reads via Playwright).

**No rate limiting or concurrency control:**
- Problem: Multiple simultaneous invocations of `sastaspace redesign` will spawn multiple Playwright browser instances and fire multiple LLM requests simultaneously. There is no mutex, queue, or concurrency limit.
- Blocks: Safe multi-user use; prevents accidental resource exhaustion on the local machine.

**No coverage enforcement in CI:**
- Problem: `pyproject.toml` and `Makefile` do not configure a coverage threshold. The `make ci` target runs `lint` and `test` but does not generate or gate on coverage reports.
- Blocks: Detecting regressions in test coverage as the codebase grows.

## Test Coverage Gaps

**`_ensure_chromium()` is entirely untested:**
- What's not tested: The Chromium auto-install logic — both the happy path and the failure path.
- Files: `sastaspace/crawler.py:15-29`
- Risk: The inverted detection logic (see Fragile Areas) could silently skip installation and cause every crawl to fail on a fresh machine.
- Priority: Medium

**Server path traversal not tested:**
- What's not tested: Requests to `GET /../../etc/passwd` or `GET /acme/../_registry.json` — whether the server correctly rejects or contains them.
- Files: `sastaspace/server.py:91-99`
- Risk: Security vulnerability exercised only in production.
- Priority: High

**`ensure_running()` timeout/failure path not tested:**
- What's not tested: The scenario where the server subprocess starts but never binds the port within the 5-second window — the function's silent return of an unlistening port.
- Files: `sastaspace/server.py:153-161`
- Risk: Users get a preview URL that returns "connection refused" with no diagnostic.
- Priority: Medium

**`redesign()` default parameter values not tested via config:**
- What's not tested: That `cli.py` actually threads `cfg.claude_code_api_url` and `cfg.claude_model` into `redesign()` correctly — tests mock `redesign` entirely rather than asserting what arguments it receives.
- Files: `sastaspace/cli.py:72`, `tests/test_cli.py:131-146`
- Risk: A config wiring bug would not be caught by the test suite.
- Priority: Low

---

*Concerns audit: 2026-03-21*
