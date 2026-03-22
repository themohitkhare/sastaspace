# Enhanced Crawl Pipeline — Design Spec

> Multi-page crawling, asset downloading, business profiling, and asset-aware redesign.

## Problem

Redesigned websites feel generic and templated because:
1. The crawler only grabs the homepage — no understanding of what the business actually does
2. No assets are downloaded — redesigns reference original domain URLs or use placeholders
3. No business intelligence — Claude doesn't know if it's looking at a dentist or a SaaS startup
4. The result doesn't feel like "their website, but better" — it feels like a stranger's website

## Solution Overview

Enhance the crawl → redesign pipeline with four new capabilities:

1. **Multi-page crawl** — Crawl homepage + up to 3 internal pages to understand the full business
2. **Asset downloading** — Download and locally store images, logos, favicons, SVGs, OG images
3. **Asset validation** — Layered security pipeline (magic bytes, Pillow, defusedxml, YARA, ClamAV)
4. **Business profiling** — LLM-extracted structured business intelligence fed to the redesign prompt

## Pipeline Flow

```
URL submitted
  │
  ├─ 1. Crawl homepage (existing crawl(), unchanged)
  │     → Extract all internal links from entire page
  │     → Download page assets (images, logo, favicon, SVGs, OG images)
  │
  ├─ 2. Smart page discovery (new)
  │     → Collect all internal links from homepage (nav, footer, content, sidebar)
  │     → Filter out noise (fragments, downloads, auth, pagination, tracking URLs)
  │     → Ask LLM to pick best 3 pages for business understanding
  │     → Crawl selected pages (lightweight: text + headings + images, no screenshot)
  │     → Download their assets too
  │
  ├─ 3. Asset validation pipeline (new)
  │     → python-magic: magic byte file type verification
  │     → Pillow .verify(): image integrity check
  │     → SVGs: defusedxml parse + nh3 whitelist sanitization
  │     → yara-python: malware pattern scan (community rules)
  │     → ClamAV (clamd via TCP): full antivirus scan
  │     → Size limits: 5MB/file, 25MB/site
  │
  ├─ 4. Business profile analysis (new)
  │     → Feed all crawled page text to LLM
  │     → Returns BusinessProfile JSON (structured)
  │     → Model-agnostic: uses whatever provider is configured
  │
  ├─ 5. Build asset manifest (new)
  │     → Map original URLs → local relative paths
  │     → e.g., https://example.com/logo.png → assets/logo.png
  │     → Passed directly to redesign LLM
  │
  └─ 6. Redesign (enhanced)
        → LLM receives: BusinessProfile + asset manifest + crawl data + screenshot
        → Generates HTML using local asset paths directly
        → Deploy writes HTML + assets/ directory
```

## Data Models

### PageCrawlResult

Lightweight crawl result for internal pages (not the full CrawlResult).

```python
@dataclass
class PageCrawlResult:
    url: str
    page_type: str          # "about", "services", "portfolio", "other"
    title: str
    headings: list[str]
    text_content: str       # 3000 chars max
    images: list[dict]      # same format as CrawlResult.images
    testimonials: list[str] # extracted quotes/review blocks
    error: str = ""
```

### DownloadedAsset

A validated, locally-stored asset.

```python
@dataclass
class DownloadedAsset:
    original_url: str
    local_path: str         # relative: "assets/logo.png"
    content_type: str       # "image/png", "image/svg+xml", etc.
    size_bytes: int
    source_page: str        # which page it came from
```

### AssetManifest

Mapping of original URLs to local paths, passed to the redesign LLM.

```python
@dataclass
class AssetManifest:
    assets: list[DownloadedAsset]
    total_size_bytes: int

    def to_prompt_context(self) -> str:
        """Renders as markdown table for LLM consumption."""
```

### BusinessProfile

Structured business intelligence extracted by LLM from all crawled pages.

```python
@dataclass
class BusinessProfile:
    business_name: str
    industry: str           # "dental", "saas", "restaurant", "agency", etc.
    services: list[str]     # what they offer
    target_audience: str    # who they serve
    tone: str               # "professional", "casual", "luxurious", "friendly"
    differentiators: list[str]  # what makes them unique
    social_proof: list[str]     # testimonials, review counts, client logos
    pricing_model: str      # "listed", "contact-based", "freemium", "subscription", "none-found"
    cta_primary: str        # their main call-to-action
    brand_personality: str  # 2-3 sentence summary
```

### EnhancedCrawlResult

Top-level result wrapping everything together.

```python
@dataclass
class EnhancedCrawlResult:
    homepage: CrawlResult           # existing, unchanged
    internal_pages: list[PageCrawlResult]  # 0-3 pages
    assets: AssetManifest
    business_profile: BusinessProfile

    def to_prompt_context(self) -> str:
        """Combines everything into structured LLM prompt."""
```

## New Modules

### `sastaspace/asset_downloader.py`

**Asset discovery** — extracts URLs from crawled HTML:
- `<img src>` and `<img srcset>`
- `<link rel="icon">` / `<link rel="shortcut icon">` (favicons)
- `<meta property="og:image">` (Open Graph)
- `<link rel="apple-touch-icon">`
- Inline `<svg>` elements (saved directly)
- Background images from inline `style` attributes (`background-image: url(...)`)

**Download logic:**
- Resolve relative URLs against page base URL
- Deduplicate across all pages (same image on homepage and services = 1 download)
- Concurrent downloads via `asyncio.gather` with semaphore (max 5 parallel)
- Timeout per download: 10s
- Skip external CDN stock photos (unsplash, pexels, shutterstock — not their assets)

**Filename strategy:**
- Slugify original filename: `Hero Banner (1).PNG` → `hero-banner-1.png`
- Prefix with source type where detectable: `logo-`, `hero-`, `og-`
- Collision handling: append `-2`, `-3`

**Validation chain** (fail = skip asset silently, don't abort pipeline):

```
download_bytes
  → size check (> 0, < 5MB)
  → python-magic: verify MIME matches allowlist
  → Pillow .verify() for raster images (png/jpg/webp/gif)
  → defusedxml parse + nh3 whitelist strip for SVGs
  → yara-python scan against community rules
  → clamd scan via TCP
  → write to sites/{subdomain}/assets/{filename}
```

**Allowlisted MIME types:** `image/png`, `image/jpeg`, `image/webp`, `image/gif`, `image/svg+xml`, `image/x-icon`, `image/vnd.microsoft.icon`

**Limits:** 10 assets per page, 30 total across all pages. 5MB per file, 25MB total per site.

### `sastaspace/business_profiler.py`

**Single LLM call** with structured extraction prompt. Sends all crawled text (homepage + internal pages) and returns `BusinessProfile` as JSON.

**Model-agnostic** — uses the same `openai.OpenAI(base_url=...)` client as the redesigner. Works with Claude, Ollama, vLLM, or any OpenAI-compatible provider.

**Extraction prompt asks for:** business_name, industry, services, target_audience, tone, differentiators, social_proof, pricing_model, cta_primary, brand_personality.

**Failure handling:** If the LLM call fails or returns unparseable JSON, return a minimal BusinessProfile with `business_name` from page title and all other fields as `"unknown"`. Pipeline continues with degraded context (still better than today's zero context).

**JSON parsing:** Try `json.loads()` first, fall back to regex extraction of JSON block from markdown-fenced response.

## Multi-Page Crawler Enhancement

### Smart Link Discovery (not hardcoded path matching)

1. **Collect all internal links** from homepage — nav, footer, sidebar, in-content. Deduplicate by URL.

2. **Filter out noise:**
   - Fragment-only links (`#section`)
   - File downloads (`.pdf`, `.zip`, `.doc`)
   - Authentication/utility (`/login`, `/cart`, `/search`, `/wp-admin`)
   - Pagination (`?page=2`, `/page/3`)
   - Very long query strings (tracking URLs)

3. **LLM picks best 3** — Send the filtered link list (URL + link text) to the LLM: *"Which 3 of these pages would give the most insight into what this business does, who they serve, and what makes them unique? Return the 3 URLs in priority order."*

4. **Fallback** — If LLM call fails or homepage has fewer than 3 internal links, crawl what's available.

### Internal Page Crawl (lightweight)

- Reuse same Playwright browser instance (session, cookies)
- No screenshot needed (only homepage screenshot goes to redesign LLM)
- Shorter text extraction: 3000 chars vs homepage's 5000
- Same 30s timeout per page
- Extract testimonials specifically: `<blockquote>`, elements with classes containing `testimonial`, `review`, `quote`, `client-say`

### New Top-Level Function

```python
async def enhanced_crawl(url: str) -> EnhancedCrawlResult:
    """Crawl homepage + up to 3 internal pages, download assets, build business profile."""
    # 1. Crawl homepage (existing crawl() function)
    # 2. Collect + filter internal links
    # 3. LLM picks best 3 pages
    # 4. Crawl internal pages (parallel, lightweight)
    # 5. Collect all asset URLs across all pages
    # 6. Download + validate assets
    # 7. Build business profile via LLM
    # 8. Build asset manifest
    # 9. Return EnhancedCrawlResult
```

Existing `crawl()` function stays untouched. Backwards compatible.

## Server Integration

### Transport: HTTP Polling (no SSE)

Frontend `POST /redesign` → gets `job_id` → polls `GET /jobs/{id}` every 3s. No SSE.

### Updated Job Status Stages

```
"crawling"     (0% → 15%)   — Homepage crawl
"discovering"  (15% → 25%)  — LLM picks pages + crawl internals
"downloading"  (25% → 40%)  — Asset download + validation
"analyzing"    (40% → 50%)  — Business profile extraction
"redesigning"  (50% → 85%)  — LLM redesign with full context
"deploying"    (85% → 100%) — Save HTML + assets to disk
"done" / "failed"           — Terminal states
```

### New Fields on Job Document (MongoDB)

```python
{
    # existing fields...
    "status": "discovering",
    "progress": 20,

    # new fields (populated progressively)
    "pages_crawled": 3,
    "assets_count": 14,
    "assets_total_size": 2841600,  # bytes
    "business_profile": {...},
}
```

### Backwards Compatibility

- CLI: existing behavior unchanged, new `--enhanced` flag for enhanced pipeline
- API: always uses enhanced pipeline
- Old job documents without new fields still work (frontend treats missing as null)

## Deployer Changes

### Updated File Structure

```
sites/{subdomain}/
├── index.html          # redesigned HTML (references assets/ paths)
├── metadata.json       # existing + assets_count, total_assets_size
└── assets/
    ├── logo.png
    ├── hero.jpg
    ├── og-image.png
    ├── icon-services.svg
    └── ...
```

- `deploy()` accepts optional `assets: list[DownloadedAsset]` parameter
- Creates `assets/` subdirectory and writes validated files
- Existing `/{subdomain}/{path}` route already serves files from subdomain directory — zero serving code changes
- Recursive cleanup on site removal catches `assets/` automatically

## Redesign Prompt Changes

### What the LLM Now Receives

```
[System prompt — updated with asset-aware instructions]

## Business Profile
- **Business:** Bright Smile Dental — dental
- **Services:** General dentistry, Cosmetic procedures, Invisalign, Teeth whitening
- **Audience:** Families and professionals in downtown Austin
- **Tone:** friendly — Warm, approachable, reassuring.
- **Differentiators:** Same-day appointments, 20 years experience, bilingual staff
- **Social proof:** "Best dentist in Austin" — Google Reviews (4.9★, 340 reviews)
- **Primary CTA:** "Book Your Free Consultation"

## Available Assets
Use these local paths in your HTML. Do NOT use placeholder images or external stock photos.

| Local Path | Description | Dimensions |
|---|---|---|
| assets/logo.png | Site logo | 200x60 |
| assets/hero.jpg | Hero/banner image | 1920x800 |
| assets/team-photo.jpg | Team/about image | 800x600 |

## Original Website Data
{existing crawl context}

[Screenshot attached as image]
```

### System Prompt Additions

- "You have access to the business's actual images. Use them. Never use placeholder URLs or stock photo services."
- "The business profile tells you who they are. Tailor the copy, layout, and emphasis to their industry and audience."
- "Preserve the brand's tone of voice."
- "Use the primary CTA prominently — it's what the business wants visitors to do."

## Infrastructure: ClamAV Sidecar

ClamAV runs as a sidecar container in the k8s `sastaspace` namespace.

- **Image:** `clamav/clamav:latest`
- **Resource:** ~3-4GB RAM for signature database
- **Expose:** TCP port 3310 (clamd) within cluster only
- **Python client:** `clamav-client` package (PyPI)
- **Freshclam:** Built into the image, auto-updates virus signatures

Backend connects to `clamd` at `clamav:3310` via the k8s service.

## New Python Dependencies

| Package | Purpose |
|---|---|
| `python-magic` | File type detection via libmagic |
| `Pillow` | Image integrity verification |
| `defusedxml` | Safe XML/SVG parsing |
| `yara-python` | Malware pattern matching |
| `clamav-client` | ClamAV daemon client |

System dependency in Docker: `libmagic1` (for python-magic).

## Timeout Budget (Worst Case)

```
Homepage crawl:     ~15s
LLM page selection: ~3s
3 internal crawls:  ~30s (parallel via asyncio)
Asset downloads:    ~10s (5 parallel, deduped)
Asset validation:   ~10s (ClamAV bottleneck)
Business profiling: ~5s
Redesign:           ~30-60s
Deploy:             ~1s
                    ─────
Total:              ~2 min worst case (vs ~1 min today)
```

The waiting screen (aurora background, insight cards, progress polling) was designed for this kind of wait.

## Codebase Integration Details

### Browser Lifecycle in `crawler.py`

The current `crawl()` function (line 148) owns the Playwright browser lifecycle — creates and destroys within `async with async_playwright()`. The `enhanced_crawl()` function needs to crawl multiple pages with a shared browser.

**Approach:** Minor refactor to `crawl()` — extract the core extraction logic into `_crawl_page(page, url) -> CrawlResult` that accepts a Playwright `Page` object. The existing `crawl()` becomes a thin wrapper that creates a browser and calls `_crawl_page()`. `enhanced_crawl()` creates its own browser, calls `_crawl_page()` for the homepage, then reuses the browser for internal pages via a lighter `_crawl_internal_page(page, url) -> PageCrawlResult`.

```python
# crawler.py — refactored structure

async def _crawl_page(page: Page, url: str) -> CrawlResult:
    """Core extraction logic, accepts an existing Playwright Page."""
    # (moved from crawl() — all the BeautifulSoup extraction, screenshot, etc.)

async def _crawl_internal_page(page: Page, url: str) -> PageCrawlResult:
    """Lightweight extraction for internal pages. No screenshot."""

async def crawl(url: str) -> CrawlResult:
    """Original public API — unchanged signature, creates its own browser."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(...)
        page = await ctx.new_page()
        result = await _crawl_page(page, url)
        await browser.close()
    return result

async def enhanced_crawl(url: str, settings: Settings) -> EnhancedCrawlResult:
    """Enhanced crawl — shared browser, multi-page, assets, business profile."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(...)
        page = await ctx.new_page()

        # 1. Homepage crawl
        homepage = await _crawl_page(page, url)

        # 2. Discover + select internal pages (LLM picks best 3)
        links = _extract_all_internal_links(homepage.html_source, url)
        selected = await _llm_select_pages(links, settings)

        # 3. Crawl internal pages (parallel via new tabs)
        internal_pages = await asyncio.gather(*[
            _crawl_internal_page(await ctx.new_page(), link)
            for link in selected
        ])

        # 4. Download + validate assets from all pages
        asset_urls = _collect_asset_urls(homepage, internal_pages)
        assets = await download_and_validate_assets(asset_urls, ...)

        # 5. Business profile via LLM
        profile = await build_business_profile(homepage, internal_pages, settings)

        await browser.close()

    return EnhancedCrawlResult(homepage, internal_pages, assets, profile)
```

The public `crawl()` signature is unchanged. CLI and tests that use `crawl()` still work. `enhanced_crawl()` is new API used by the worker.

### Redesigner Interface (`redesigner.py`)

The current `_redesign_with_prompts()` (line 84) and `run_redesign()` (line 342) accept `CrawlResult`. Two changes:

1. **`run_redesign()` gets a new optional parameter:**

```python
def run_redesign(
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "standard",
    progress_callback=None,
    checkpoint: dict | None = None,
    checkpoint_callback=None,
    enhanced: EnhancedCrawlResult | None = None,  # NEW
) -> str:
```

2. **When `enhanced` is provided**, the prompt context is built from `enhanced.to_prompt_context()` instead of `crawl_result.to_prompt_context()`. The `crawl_result` parameter still provides the screenshot for the API call. This way existing callers (CLI, tests) pass just `crawl_result` and everything works. The worker passes both.

3. **`EnhancedCrawlResult.to_prompt_context()`** produces the enriched prompt with business profile + asset manifest + crawl data (as shown in Section 8 of this spec).

### Worker Handler (`jobs.py`)

The `redesign_handler()` (line 323 of `jobs.py`) is the actual pipeline orchestrator. It currently runs 3 steps: Crawl → Redesign → Deploy.

**Updated handler flow (6 steps):**

```python
async def redesign_handler(job_id, url, tier, job_service, checkpoint=None):
    settings = Settings()

    # Step 1: Crawling (0% → 15%)
    await update_job(job_id, status="crawling", progress=10, ...)
    await job_service.publish_status(job_id, "crawling", {...})
    # Uses enhanced_crawl() which handles steps 1-4 internally
    # but we break out progress updates via callbacks

    enhanced_result = await enhanced_crawl(
        url, settings,
        progress_callback=lambda stage, pct: ...,  # publishes status updates
    )
    # enhanced_crawl internally:
    #   - crawls homepage (0%→15%)
    #   - discovers + crawls internal pages (15%→25%)
    #   - downloads + validates assets (25%→40%)
    #   - builds business profile (40%→50%)

    # Step 2: Redesigning (50% → 85%)
    await update_job(job_id, status="redesigning", progress=50, ...)
    html = await asyncio.to_thread(
        run_redesign,
        enhanced_result.homepage,  # CrawlResult for screenshot
        settings, tier,
        _on_agent_progress, pipeline_checkpoint, _on_checkpoint,
        enhanced=enhanced_result,  # NEW: full enhanced context
    )

    # Step 3: Deploying (85% → 100%)
    await update_job(job_id, status="deploying", progress=85, ...)
    result = await asyncio.to_thread(
        deploy, url, html, settings.sites_dir,
        assets=enhanced_result.assets.assets,  # NEW: write assets
    )

    # Done
    await update_job(job_id, status="done", progress=100, ...)
```

**Checkpoint support:** The existing checkpoint mechanism persists `crawl_result` after step 1. Extended to also persist `enhanced_crawl` intermediate results (internal pages, assets, business profile) so recovered jobs can skip completed steps.

### JobStatus Enum (`database.py`)

Add new status values to `JobStatus`:

```python
class JobStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    DISCOVERING = "discovering"    # NEW
    DOWNLOADING = "downloading"    # NEW
    ANALYZING = "analyzing"        # NEW
    REDESIGNING = "redesigning"
    DEPLOYING = "deploying"
    DONE = "done"
    FAILED = "failed"
```

### `update_job()` New Parameters (`database.py`)

Add new keyword arguments to `update_job()`:

```python
async def update_job(
    job_id: str,
    *,
    # existing params...
    pages_crawled: int | None = None,       # NEW
    assets_count: int | None = None,        # NEW
    assets_total_size: int | None = None,   # NEW
    business_profile: dict | None = None,   # NEW
) -> None:
```

### Deployer Changes (`deployer.py`)

Updated `deploy()` signature:

```python
def deploy(
    url: str,
    html: str,
    sites_dir: Path,
    subdomain: str | None = None,
    assets: list[DownloadedAsset] | None = None,  # NEW
) -> DeployResult:
```

When `assets` is provided:
1. Create `site_dir / "assets"` directory
2. Each `DownloadedAsset` carries `file_bytes: bytes` (held in memory from download/validation step)
3. Write each asset to `site_dir / asset.local_path`
4. Update `metadata.json` to include `assets_count` and `total_assets_size`

The `_registry.json` flat file continues to exist alongside MongoDB — it's used by the CLI `list` command and the server's admin dashboard (`GET /`). No changes needed to registry format.

### Asset Storage Flow

Assets are downloaded to memory (bytes), validated in memory, and only written to disk by the deployer:

```
Download → bytes in memory
  → validate in memory (magic bytes, Pillow, defusedxml, YARA, ClamAV)
  → store validated bytes on DownloadedAsset.file_bytes
  → deployer writes to sites/{subdomain}/assets/{filename}
```

No temp directory needed. Assets never touch disk until they pass all validation.

### `DownloadedAsset` Updated

```python
@dataclass
class DownloadedAsset:
    original_url: str
    local_path: str         # relative: "assets/logo.png"
    content_type: str       # "image/png", "image/svg+xml", etc.
    size_bytes: int
    source_page: str        # which page it came from
    file_bytes: bytes       # validated file content, written by deployer
```

## Edge Cases

### Sites Requiring Authentication
Internal page crawls that redirect to a login page (HTTP 302/303 to `/login`, `/signin`, or URL containing `auth`/`login`) are detected and skipped. The pipeline continues with fewer internal pages.

### Sites With No Images
When `AssetManifest.assets` is empty, the redesign prompt omits the "Available Assets" section entirely and instead includes: "No downloadable assets found. Use CSS gradients, solid colors, and geometric shapes for visual interest. Do not reference external image URLs."

### SPA / JavaScript-Rendered Sites
Link extraction uses Playwright's live DOM (`page.content()`) after `networkidle`, which captures JS-rendered content. BeautifulSoup parses the post-render HTML, so SPAs that hydrate nav links via JS are handled.

### Sites With Many Links
Cap link extraction at 50 internal links before sending to the LLM for selection. Sort by DOM order (links appearing earlier in the page are more likely to be important).

### Bot Protection on Internal Pages
If an internal page returns a non-200 status or the page content is shorter than 500 characters (likely a challenge page), skip it silently. Log a warning.

### Data URIs and Blob URLs
Skip `data:` URIs (already inline, no need to download). Skip `blob:` URLs (not downloadable). Skip URLs with query strings longer than 256 characters (likely CDN transforms — download without query params as fallback).

### Duplicate Content Across Pages
Before sending to the business profiler LLM, deduplicate text by paragraph. If a paragraph appears on 2+ pages (header/footer boilerplate), include it only once and mark it as "site-wide" content.

### Existing Deployed Sites (Migration)
Old sites in `sites/{subdomain}/` without an `assets/` directory continue to work. The `/{subdomain}/{path}` route returns 404 for missing files, which is the correct behavior. No migration needed.

## Testing Strategy

### Unit Tests
- `test_asset_downloader.py` — Mock HTTP responses, test MIME validation, size limits, filename slugification, deduplication, stock photo CDN skip list
- `test_business_profiler.py` — Mock LLM responses (valid JSON, malformed JSON, empty response), test fallback to minimal profile
- `test_crawler_enhanced.py` — Mock Playwright, test link extraction, link filtering (noise removal), internal page crawl, `enhanced_crawl()` end-to-end with mocks
- `test_deployer.py` — Extend existing tests for `assets` parameter, verify `assets/` directory creation, metadata fields

### Integration Tests (require running services)
- ClamAV validation: test with EICAR test file (standard antivirus test string)
- YARA scanning: test with a rule that matches a known test pattern
- Full pipeline: `enhanced_crawl()` against a local test server with known pages/assets

### CI Considerations
- ClamAV not available in CI — mock the `clamd` client in unit tests, skip ClamAV integration tests in CI
- YARA rules bundled in the repo under `sastaspace/yara_rules/` — loaded at module import time
- `python-magic` requires `libmagic1` — add to CI apt install step and backend Dockerfile

## New Python Dependencies

| Package | Purpose | System Dep |
|---|---|---|
| `python-magic` | File type detection via libmagic | `libmagic1` (apt) / `brew install libmagic` (macOS) |
| `Pillow` | Image integrity verification | None |
| `defusedxml` | Safe XML/SVG parsing | None |
| `yara-python` | Malware pattern matching | None (compiles C extension) |
| `clamav-client` | ClamAV daemon client | ClamAV daemon running |

## Infrastructure: ClamAV

ClamAV runs as a separate deployment (not sidecar) in the `sastaspace` k8s namespace.

- **Image:** `clamav/clamav:latest`
- **Resource requests:** 512Mi RAM, 100m CPU / **Limits:** 4Gi RAM, 500m CPU
- **Service:** `clamav:3310` (TCP, ClusterIP, internal only)
- **Freshclam:** Built into the image, auto-updates virus signatures
- **k8s manifest:** `k8s/clamav.yaml` (new file)
- **Fallback:** If ClamAV service is unreachable, skip the ClamAV scan step and log a warning. All other validation layers still run.

### YARA Rules

Bundle a curated, minimal set of YARA rules focused on:
- JavaScript/VBScript embedded in image files
- Known image-based exploit patterns (e.g., polyglot files)
- Suspicious SVG content (script tags, event handlers — belt-and-suspenders with defusedxml)

Rules stored in `sastaspace/yara_rules/*.yar`, loaded once at module import. Not the full community ruleset — a focused set of ~20-30 rules for image-specific threats.

## Timeout Budget (Worst Case)

```
Homepage crawl:      ~15s
LLM page selection:  ~3s
3 internal crawls:   ~30s (parallel via asyncio)
Asset downloads:     ~10s (5 parallel, deduped)
Asset validation:    ~10s (ClamAV bottleneck)
Business profiling:  ~5s
Redesign:            ~30-60s
Deploy:              ~1s
                     ─────
Total:               ~2 min worst case (vs ~1 min today)
```

The waiting screen (aurora background, insight cards, progress polling) was designed for this kind of wait.

### LLM Call Budget Per Redesign

| Call | Purpose | Input Size | Output Size |
|---|---|---|---|
| 1 | Page selection | ~50 links (URL + text) | 3 URLs |
| 2 | Business profile | ~10K chars text | ~500 chars JSON |
| 3 | Redesign | Screenshot + profile + manifest + crawl context | ~16-20K tokens HTML |

Calls 1 and 2 are cheap (~1K tokens each). All calls use the configured provider (model-agnostic).

## What Stays the Same

- Single HTML file output with inline CSS
- Google Fonts for typography
- Responsive design requirement
- `nh3` sanitization of redesign output
- HTML validation (DOCTYPE, closing tag check)
- Rate limiting, dedup, concurrency control
- Frontend polling transport
- CLI basic commands (redesign, list, open, remove, serve)
- `_registry.json` flat file (coexists with MongoDB)
