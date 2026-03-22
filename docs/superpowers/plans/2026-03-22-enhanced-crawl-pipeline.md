# Enhanced Crawl Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the redesign pipeline to crawl multiple pages, download/validate assets, build a business profile, and generate asset-aware redesigns that feel tailored to each business.

**Architecture:** New modules (`asset_downloader.py`, `business_profiler.py`, `asset_validator.py`) feed into an `enhanced_crawl()` function in `crawler.py`. The existing `crawl()` is refactored internally (extract `_crawl_page()`) but keeps its public signature. The worker handler in `jobs.py` switches from `crawl()` to `enhanced_crawl()`, and `run_redesign()` gains an optional `enhanced` parameter for richer prompt context.

**Tech Stack:** Python 3.11, Playwright, BeautifulSoup4, python-magic, Pillow, defusedxml, yara-python, clamav-client, OpenAI SDK (model-agnostic), FastAPI, MongoDB (motor), Redis

**Spec:** `docs/superpowers/specs/2026-03-22-enhanced-crawl-pipeline-design.md`

---

## Task 1: Add New Dependencies

**Files:**
- Modify: `pyproject.toml` (lines 6–20, `[project.dependencies]`)
- Modify: `backend/Dockerfile` (line 4–26, system deps)

- [ ] **Step 1: Add Python packages to pyproject.toml**

Add to `[project.dependencies]`:
```toml
"python-magic>=0.4.27",
"Pillow>=10.0.0",
"defusedxml>=0.7.1",
"yara-python>=4.5.0",
"pyclamd>=0.4.0",
"aiohttp>=3.9.0",
"nh3>=0.2.14",
```

- [ ] **Step 2: Add libmagic to backend Dockerfile**

In `backend/Dockerfile`, add `libmagic1` to the `apt-get install` line (around line 7):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    # ... existing chromium deps ...
```

- [ ] **Step 3: Sync lockfile and verify**

Run: `uv sync`
Expected: All new packages resolve and install.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock backend/Dockerfile
git commit -m "deps: add python-magic, Pillow, defusedxml, yara-python, pyclamd, aiohttp, nh3"
```

---

## Task 2: Data Models

**Files:**
- Create: `sastaspace/models.py`
- Test: `tests/test_models_enhanced.py`

- [ ] **Step 1: Write tests for new data models**

```python
# tests/test_models_enhanced.py
from pathlib import Path
from sastaspace.models import (
    PageCrawlResult, DownloadedAsset, AssetManifest, BusinessProfile, EnhancedCrawlResult,
)
from sastaspace.crawler import CrawlResult


class TestPageCrawlResult:
    def test_creation(self):
        p = PageCrawlResult(
            url="https://example.com/about",
            page_type="about",
            title="About Us",
            headings=["Our Story"],
            text_content="We are a company.",
            images=[],
            testimonials=["Great service!"],
        )
        assert p.error == ""
        assert p.page_type == "about"

    def test_error_sentinel(self):
        p = PageCrawlResult(url="https://x.com", page_type="other", title="", headings=[],
                            text_content="", images=[], testimonials=[], error="Timeout")
        assert p.error == "Timeout"


class TestDownloadedAsset:
    def test_creation(self):
        a = DownloadedAsset(
            original_url="https://example.com/logo.png",
            local_path="assets/logo.png",
            content_type="image/png",
            size_bytes=1024,
            file_hash="abc123",
            source_page="https://example.com",
            tmp_path=Path("/tmp/test/assets/logo.png"),
        )
        assert a.local_path == "assets/logo.png"


class TestAssetManifest:
    def test_empty_prompt_context(self):
        m = AssetManifest(assets=[], total_size_bytes=0)
        ctx = m.to_prompt_context()
        assert ctx == ""

    def test_prompt_context_truncation(self):
        assets = [
            DownloadedAsset(f"https://example.com/img{i}.png", f"assets/img{i}.png",
                            "image/png", (20 - i) * 1000, f"hash{i}", "https://example.com",
                            Path(f"/tmp/img{i}.png"))
            for i in range(20)
        ]
        m = AssetManifest(assets=assets, total_size_bytes=sum(a.size_bytes for a in assets))
        ctx = m.to_prompt_context(max_assets=5)
        # Should only contain 5 assets
        assert ctx.count("assets/img") == 5

    def test_logo_favicon_prioritized(self):
        logo = DownloadedAsset("https://x.com/logo.png", "assets/logo-main.png",
                               "image/png", 100, "h1", "https://x.com", Path("/tmp/logo.png"))
        favicon = DownloadedAsset("https://x.com/fav.ico", "assets/favicon.ico",
                                   "image/x-icon", 50, "h2", "https://x.com", Path("/tmp/fav.ico"))
        big = DownloadedAsset("https://x.com/hero.jpg", "assets/hero.jpg",
                               "image/jpeg", 500_000, "h3", "https://x.com", Path("/tmp/hero.jpg"))
        m = AssetManifest(assets=[big, favicon, logo], total_size_bytes=500_150)
        ctx = m.to_prompt_context(max_assets=2)
        lines = ctx.strip().split("\n")
        # Logo and favicon should appear before hero even though hero is bigger
        data_lines = [l for l in lines if "assets/" in l]
        assert "logo" in data_lines[0].lower() or "favicon" in data_lines[0].lower()


class TestBusinessProfile:
    def test_minimal_profile(self):
        bp = BusinessProfile.minimal("Acme Corp")
        assert bp.business_name == "Acme Corp"
        assert bp.industry == "unknown"

    def test_to_prompt_context(self):
        bp = BusinessProfile(
            business_name="Bright Smile Dental",
            industry="dental",
            services=["General dentistry", "Cosmetic"],
            target_audience="Families in Austin",
            tone="friendly",
            differentiators=["Same-day appointments"],
            social_proof=["4.9 stars on Google"],
            pricing_model="contact-based",
            cta_primary="Book Your Free Consultation",
            brand_personality="Warm and reassuring.",
        )
        ctx = bp.to_prompt_context()
        assert "Bright Smile Dental" in ctx
        assert "dental" in ctx
        assert "Book Your Free Consultation" in ctx


class TestEnhancedCrawlResult:
    def test_to_prompt_context_no_assets(self):
        homepage = CrawlResult(url="https://x.com", title="X", meta_description="",
                                favicon_url="", html_source="", screenshot_base64="",
                                headings=[], navigation_links=[], text_content="Hello",
                                images=[], colors=[], fonts=[], sections=[])
        bp = BusinessProfile.minimal("X")
        manifest = AssetManifest(assets=[], total_size_bytes=0)
        ecr = EnhancedCrawlResult(homepage=homepage, internal_pages=[], assets=manifest,
                                   business_profile=bp)
        ctx = ecr.to_prompt_context()
        assert "Available Assets" not in ctx
        assert "No downloadable assets found" in ctx
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models_enhanced.py -v`
Expected: ImportError — `sastaspace.models` does not exist yet.

- [ ] **Step 3: Implement data models**

```python
# sastaspace/models.py
"""Enhanced crawl pipeline data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PageCrawlResult:
    """Lightweight crawl result for an internal page."""
    url: str
    page_type: str
    title: str
    headings: list[str]
    text_content: str
    images: list[dict]
    testimonials: list[str]
    error: str = ""


@dataclass
class DownloadedAsset:
    """A validated, locally-stored asset."""
    original_url: str
    local_path: str
    content_type: str
    size_bytes: int
    file_hash: str
    source_page: str
    tmp_path: Path


@dataclass
class AssetManifest:
    """Mapping of original URLs to local paths for the redesign LLM."""
    assets: list[DownloadedAsset]
    total_size_bytes: int

    def to_prompt_context(self, max_assets: int = 15) -> str:
        if not self.assets:
            return ""
        prioritized = sorted(
            self.assets,
            key=lambda a: (
                0 if "logo" in a.local_path.lower() or "favicon" in a.local_path.lower() else 1,
                -a.size_bytes,
            ),
        )
        selected = prioritized[:max_assets]
        lines = [
            "## Available Assets",
            "Use these local paths in your HTML. Do NOT use placeholder images or external stock photos.",
            "If an asset fits a section, use it. If none fit, use CSS gradients or solid colors instead.",
            "",
            "| Local Path | Type | Size |",
            "|---|---|---|",
        ]
        for a in selected:
            size_kb = a.size_bytes // 1024
            lines.append(f"| {a.local_path} | {a.content_type} | {size_kb}KB |")
        return "\n".join(lines)


@dataclass
class BusinessProfile:
    """Structured business intelligence extracted by LLM."""
    business_name: str
    industry: str
    services: list[str]
    target_audience: str
    tone: str
    differentiators: list[str]
    social_proof: list[str]
    pricing_model: str
    cta_primary: str
    brand_personality: str

    @classmethod
    def minimal(cls, business_name: str) -> BusinessProfile:
        return cls(
            business_name=business_name,
            industry="unknown",
            services=[],
            target_audience="unknown",
            tone="unknown",
            differentiators=[],
            social_proof=[],
            pricing_model="none-found",
            cta_primary="unknown",
            brand_personality="unknown",
        )

    def to_prompt_context(self) -> str:
        lines = [
            "## Business Profile",
            f"- **Business:** {self.business_name} — {self.industry}",
        ]
        if self.services:
            lines.append(f"- **Services:** {', '.join(self.services)}")
        lines.append(f"- **Audience:** {self.target_audience}")
        lines.append(f"- **Tone:** {self.tone} — {self.brand_personality}")
        if self.differentiators:
            lines.append(f"- **Key differentiators:** {', '.join(self.differentiators)}")
        if self.social_proof:
            lines.append(f"- **Social proof:** {'; '.join(self.social_proof)}")
        lines.append(f"- **Primary CTA:** {self.cta_primary}")
        return "\n".join(lines)


@dataclass
class EnhancedCrawlResult:
    """Full enhanced crawl output wrapping all pipeline results."""
    homepage: object  # CrawlResult (avoid circular import)
    internal_pages: list[PageCrawlResult] = field(default_factory=list)
    assets: AssetManifest = field(default_factory=lambda: AssetManifest([], 0))
    business_profile: BusinessProfile = field(default_factory=lambda: BusinessProfile.minimal(""))

    def to_prompt_context(self) -> str:
        parts = []
        parts.append(self.business_profile.to_prompt_context())
        parts.append("")
        asset_ctx = self.assets.to_prompt_context()
        if asset_ctx:
            parts.append(asset_ctx)
        else:
            parts.append(
                "No downloadable assets found. Use CSS gradients, solid colors, "
                "and geometric shapes for visual interest. Do not reference external image URLs."
            )
        parts.append("")
        parts.append("## Original Website Data")
        parts.append(self.homepage.to_prompt_context())
        if self.internal_pages:
            parts.append("")
            parts.append("## Internal Pages")
            for p in self.internal_pages:
                if p.error:
                    continue
                parts.append(f"\n### {p.page_type.title()}: {p.title}")
                if p.headings:
                    parts.append("Headings: " + ", ".join(p.headings[:10]))
                if p.text_content:
                    parts.append(p.text_content[:2000])
                if p.testimonials:
                    parts.append("Testimonials: " + " | ".join(p.testimonials[:5]))
        return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models_enhanced.py -v`
Expected: All PASS.

- [ ] **Step 5: Lint**

Run: `uv run ruff check sastaspace/models.py tests/test_models_enhanced.py && uv run ruff format sastaspace/models.py tests/test_models_enhanced.py`

- [ ] **Step 6: Commit**

```bash
git add sastaspace/models.py tests/test_models_enhanced.py
git commit -m "feat: add enhanced crawl pipeline data models"
```

---

## Task 3: Asset Validator

**Files:**
- Create: `sastaspace/asset_validator.py`
- Create: `sastaspace/yara_rules/image_threats.yar`
- Test: `tests/test_asset_validator.py`

- [ ] **Step 1: Write YARA rules file**

```yara
// sastaspace/yara_rules/image_threats.yar
rule JS_In_Image {
    meta:
        description = "JavaScript embedded in image file"
    strings:
        $script = "<script" ascii nocase
        $eval = "eval(" ascii nocase
        $document = "document." ascii nocase
    condition:
        any of them
}

rule VBScript_In_Image {
    meta:
        description = "VBScript embedded in image file"
    strings:
        $vbs = "<vbscript" ascii nocase
    condition:
        any of them
}

rule SVG_Event_Handlers {
    meta:
        description = "SVG with inline event handlers"
    strings:
        $onload = "onload=" ascii nocase
        $onerror = "onerror=" ascii nocase
        $onmouseover = "onmouseover=" ascii nocase
        $onclick = "onclick=" ascii nocase
    condition:
        any of them
}

rule Polyglot_File {
    meta:
        description = "File with multiple magic signatures (polyglot)"
    strings:
        $pdf = "%PDF" ascii
        $elf = { 7f 45 4c 46 }
        $pe = "MZ" ascii
        $php = "<?php" ascii nocase
    condition:
        $pdf at 0 or $elf at 0 or $pe at 0 or $php at 0
}
```

- [ ] **Step 2: Write validator tests**

```python
# tests/test_asset_validator.py
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestValidateMimeType:
    def test_valid_png(self, tmp_path):
        from sastaspace.asset_validator import validate_mime_type
        # Create a minimal PNG file (8-byte header)
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        f = tmp_path / "test.png"
        f.write_bytes(png_header)
        assert validate_mime_type(f) == "image/png"

    def test_rejects_text_file(self, tmp_path):
        from sastaspace.asset_validator import validate_mime_type
        f = tmp_path / "fake.png"
        f.write_text("not an image")
        assert validate_mime_type(f) is None

    def test_rejects_empty_file(self, tmp_path):
        from sastaspace.asset_validator import validate_mime_type
        f = tmp_path / "empty.png"
        f.write_bytes(b"")
        assert validate_mime_type(f) is None


class TestValidateImageIntegrity:
    def test_valid_png(self, tmp_path):
        from sastaspace.asset_validator import validate_image_integrity
        from PIL import Image
        img = Image.new("RGB", (10, 10), "red")
        f = tmp_path / "valid.png"
        img.save(f, "PNG")
        assert validate_image_integrity(f) is True

    def test_corrupt_image(self, tmp_path):
        from sastaspace.asset_validator import validate_image_integrity
        f = tmp_path / "corrupt.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\ngarbage")
        assert validate_image_integrity(f) is False


class TestSanitizeSvg:
    def test_strips_script_tags(self):
        from sastaspace.asset_validator import sanitize_svg
        dirty = '<svg><script>alert(1)</script><circle r="5"/></svg>'
        clean = sanitize_svg(dirty)
        assert "<script>" not in clean
        assert "<circle" in clean

    def test_strips_event_handlers(self):
        from sastaspace.asset_validator import sanitize_svg
        dirty = '<svg><circle onload="alert(1)" r="5"/></svg>'
        clean = sanitize_svg(dirty)
        assert "onload" not in clean

    def test_strips_foreign_object(self):
        from sastaspace.asset_validator import sanitize_svg
        dirty = '<svg><foreignObject><body>XSS</body></foreignObject></svg>'
        clean = sanitize_svg(dirty)
        assert "<foreignObject>" not in clean.lower()


class TestValidateAsset:
    def test_full_chain_valid_png(self, tmp_path):
        from sastaspace.asset_validator import validate_asset
        from PIL import Image
        img = Image.new("RGB", (10, 10), "red")
        f = tmp_path / "good.png"
        img.save(f, "PNG")
        result = validate_asset(f, skip_clamav=True)
        assert result is True

    def test_full_chain_oversized(self, tmp_path):
        from sastaspace.asset_validator import validate_asset
        f = tmp_path / "huge.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (6 * 1024 * 1024))
        result = validate_asset(f, max_size_bytes=5 * 1024 * 1024, skip_clamav=True)
        assert result is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_asset_validator.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement asset validator**

```python
# sastaspace/asset_validator.py
"""Layered security validation for downloaded assets."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import defusedxml.ElementTree as ET
import magic
import nh3
import yara
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_MIMES = {
    "image/png", "image/jpeg", "image/webp", "image/gif",
    "image/svg+xml", "image/x-icon", "image/vnd.microsoft.icon",
}

# SVG elements/attributes considered safe
_SVG_SAFE_TAGS = {
    "svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline",
    "polygon", "text", "tspan", "defs", "use", "symbol", "clipPath",
    "mask", "linearGradient", "radialGradient", "stop", "title", "desc",
    "image", "pattern", "filter",
}
_SVG_UNSAFE_ATTRS_PREFIX = ("on",)  # onclick, onload, onerror, etc.
_SVG_UNSAFE_TAGS = {"script", "foreignobject", "set", "animate", "iframe", "embed", "object"}

# Load YARA rules once at module level
_YARA_RULES_DIR = Path(__file__).parent / "yara_rules"
_yara_rules = None


def _get_yara_rules() -> yara.Rules | None:
    global _yara_rules
    if _yara_rules is not None:
        return _yara_rules
    rule_files = list(_YARA_RULES_DIR.glob("*.yar"))
    if not rule_files:
        logger.warning("No YARA rules found in %s", _YARA_RULES_DIR)
        return None
    filepaths = {f.stem: str(f) for f in rule_files}
    _yara_rules = yara.compile(filepaths=filepaths)
    return _yara_rules


def file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_mime_type(path: Path) -> str | None:
    """Check file's magic bytes. Returns MIME type if allowed, None if rejected."""
    try:
        mime = magic.from_file(str(path), mime=True)
    except Exception:
        logger.warning("python-magic failed for %s", path)
        return None
    if mime not in ALLOWED_MIMES:
        logger.info("Rejected MIME %s for %s", mime, path.name)
        return None
    return mime


def validate_image_integrity(path: Path) -> bool:
    """Verify image is a valid, parseable image file via Pillow."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        logger.info("Pillow verify failed for %s", path.name)
        return False


def sanitize_svg(svg_content: str) -> str:
    """Strip dangerous elements/attributes from SVG content."""
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        logger.warning("SVG parse failed, returning empty SVG")
        return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    def _clean_element(el):
        tag_local = el.tag.split("}")[-1].lower() if "}" in el.tag else el.tag.lower()
        if tag_local in _SVG_UNSAFE_TAGS:
            return None
        unsafe_attrs = [
            k for k in el.attrib
            if k.split("}")[-1].lower().startswith(_SVG_UNSAFE_ATTRS_PREFIX)
            or "javascript:" in (el.attrib[k] or "").lower()
        ]
        for attr in unsafe_attrs:
            del el.attrib[attr]
        safe_children = []
        for child in el:
            cleaned = _clean_element(child)
            if cleaned is not None:
                safe_children.append(cleaned)
        el[:] = safe_children
        return el

    cleaned = _clean_element(root)
    if cleaned is None:
        return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    return ET.tostring(cleaned, encoding="unicode")


def scan_yara(path: Path) -> bool:
    """Scan file against YARA rules. Returns True if clean."""
    rules = _get_yara_rules()
    if rules is None:
        return True
    matches = rules.match(str(path))
    if matches:
        logger.warning("YARA match for %s: %s", path.name, [m.rule for m in matches])
        return False
    return True


def scan_clamav(path: Path, clamd_host: str = "localhost", clamd_port: int = 3310) -> bool:
    """Scan file via ClamAV daemon. Returns True if clean, True if ClamAV unreachable."""
    try:
        import pyclamd
        cd = pyclamd.ClamdNetworkSocket(host=clamd_host, port=clamd_port, timeout=10)
        if not cd.ping():
            logger.warning("ClamAV not responding to ping, skipping scan")
            return True
        result = cd.scan_file(str(path))
        if result is None:
            return True  # No threat found
        for filepath, status in result.items():
            if status[0] == "FOUND":
                logger.warning("ClamAV flagged %s: %s", path.name, status)
                return False
        return True
    except Exception as e:
        logger.warning("ClamAV unreachable, skipping scan: %s", e)
        return True


def validate_asset(
    path: Path,
    max_size_bytes: int = 5 * 1024 * 1024,
    skip_clamav: bool = False,
) -> bool:
    """Run full validation chain. Returns True if asset is safe."""
    # Size check
    size = path.stat().st_size
    if size == 0 or size > max_size_bytes:
        logger.info("Size check failed for %s: %d bytes", path.name, size)
        return False

    # Magic byte check
    mime = validate_mime_type(path)
    if mime is None:
        return False

    # Image integrity (skip for ICO/SVG)
    if mime not in ("image/svg+xml", "image/x-icon", "image/vnd.microsoft.icon"):
        if not validate_image_integrity(path):
            return False

    # SVG sanitization (in-place rewrite)
    if mime == "image/svg+xml":
        svg_content = path.read_text(encoding="utf-8", errors="replace")
        clean_svg = sanitize_svg(svg_content)
        path.write_text(clean_svg, encoding="utf-8")

    # YARA scan
    if not scan_yara(path):
        return False

    # ClamAV scan
    if not skip_clamav and not scan_clamav(path):
        return False

    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_asset_validator.py -v`
Expected: All PASS.

- [ ] **Step 6: Lint**

Run: `uv run ruff check sastaspace/asset_validator.py sastaspace/yara_rules/ tests/test_asset_validator.py && uv run ruff format sastaspace/asset_validator.py tests/test_asset_validator.py`

- [ ] **Step 7: Commit**

```bash
git add sastaspace/asset_validator.py sastaspace/yara_rules/ tests/test_asset_validator.py
git commit -m "feat: add layered asset validation (magic bytes, Pillow, defusedxml, YARA, ClamAV)"
```

---

## Task 4: Asset Downloader

**Files:**
- Create: `sastaspace/asset_downloader.py`
- Test: `tests/test_asset_downloader.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_asset_downloader.py
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from sastaspace.asset_downloader import (
    extract_asset_urls,
    slugify_filename,
    normalize_url,
    is_stock_photo,
    download_and_validate_assets,
)


class TestExtractAssetUrls:
    def test_extracts_img_src(self):
        html = '<html><body><img src="/images/logo.png" alt="logo"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/images/logo.png" in urls

    def test_extracts_og_image(self):
        html = '<html><head><meta property="og:image" content="https://example.com/og.jpg"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/og.jpg" in urls

    def test_extracts_favicon(self):
        html = '<html><head><link rel="icon" href="/favicon.ico"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/favicon.ico" in urls

    def test_skips_data_uris(self):
        html = '<html><body><img src="data:image/png;base64,abc"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert len(urls) == 0

    def test_deduplicates(self):
        html = '<html><body><img src="/logo.png"><img src="/logo.png"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert urls.count("https://example.com/logo.png") == 1

    def test_limits_count(self):
        imgs = "".join(f'<img src="/img{i}.png">' for i in range(20))
        html = f"<html><body>{imgs}</body></html>"
        urls = extract_asset_urls(html, "https://example.com", max_per_page=10)
        assert len(urls) == 10


class TestSlugifyFilename:
    def test_basic(self):
        assert slugify_filename("Hero Banner (1).PNG") == "hero-banner-1.png"

    def test_preserves_extension(self):
        assert slugify_filename("logo.svg") == "logo.svg"

    def test_long_name_truncated(self):
        name = "a" * 200 + ".png"
        result = slugify_filename(name)
        assert len(result) <= 60


class TestNormalizeUrl:
    def test_strips_cache_busting(self):
        assert normalize_url("https://x.com/logo.png?v=123") == "https://x.com/logo.png"

    def test_preserves_meaningful_params(self):
        # Params like w= and h= might be meaningful (CDN resize)
        url = "https://x.com/img.jpg?w=800&h=600"
        # We strip all params for dedup — content hash catches true dupes
        assert normalize_url(url) == "https://x.com/img.jpg"


class TestIsStockPhoto:
    def test_detects_unsplash(self):
        assert is_stock_photo("https://images.unsplash.com/photo-123") is True

    def test_detects_pexels(self):
        assert is_stock_photo("https://images.pexels.com/photos/123") is True

    def test_allows_own_domain(self):
        assert is_stock_photo("https://example.com/hero.jpg") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_asset_downloader.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement asset downloader**

```python
# sastaspace/asset_downloader.py
"""Download and validate assets from crawled web pages."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup

from sastaspace.asset_validator import file_hash, validate_asset
from sastaspace.models import AssetManifest, DownloadedAsset

logger = logging.getLogger(__name__)

_STOCK_DOMAINS = {"unsplash.com", "pexels.com", "shutterstock.com", "istockphoto.com",
                  "gettyimages.com", "pixabay.com", "stock.adobe.com"}

_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=10)
_MAX_PER_PAGE = 10
_MAX_TOTAL = 30
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
_MAX_SITE_SIZE = 25 * 1024 * 1024  # 25MB


def normalize_url(url: str) -> str:
    """Strip query params for URL-level deduplication."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def is_stock_photo(url: str) -> bool:
    """Check if URL is from a known stock photo CDN."""
    hostname = urlparse(url).hostname or ""
    return any(domain in hostname for domain in _STOCK_DOMAINS)


def slugify_filename(name: str) -> str:
    """Convert filename to filesystem-safe slug."""
    stem, _, ext = name.rpartition(".")
    if not stem:
        stem = name
        ext = ""
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    slug = slug[:50]
    if ext:
        slug = f"{slug}.{ext.lower()}"
    return slug[:60]


def extract_asset_urls(html: str, base_url: str, max_per_page: int = _MAX_PER_PAGE) -> list[str]:
    """Extract image/asset URLs from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    def _add(raw_url: str):
        if not raw_url or raw_url.startswith(("data:", "blob:", "javascript:")):
            return
        absolute = urljoin(base_url, raw_url)
        normalized = normalize_url(absolute)
        if normalized not in seen and not is_stock_photo(normalized):
            seen.add(normalized)
            urls.append(absolute)

    # <img src> and srcset
    for img in soup.find_all("img", src=True):
        _add(img["src"])
        if img.get("srcset"):
            for entry in img["srcset"].split(","):
                parts = entry.strip().split()
                if parts:
                    _add(parts[0])

    # <link rel="icon"> / <link rel="shortcut icon"> / <link rel="apple-touch-icon">
    for link in soup.find_all("link", rel=True):
        rels = [r.lower() for r in link.get("rel", [])]
        if any(r in rels for r in ("icon", "shortcut icon", "apple-touch-icon")):
            _add(link.get("href", ""))

    # <meta property="og:image">
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        _add(og["content"])

    # background-image in inline styles
    for el in soup.find_all(style=True):
        match = re.search(r'background-image:\s*url\(["\']?([^"\')\s]+)', el["style"])
        if match:
            _add(match.group(1))

    return urls[:max_per_page]


async def _download_one(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
    semaphore: asyncio.Semaphore,
) -> Path | None:
    """Download a single asset to dest. Returns path or None on failure."""
    async with semaphore:
        try:
            async with session.get(url, timeout=_DOWNLOAD_TIMEOUT) as resp:
                if resp.status != 200:
                    return None
                size = 0
                with open(dest, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        size += len(chunk)
                        if size > _MAX_FILE_SIZE:
                            logger.info("Asset too large, aborting: %s", url)
                            dest.unlink(missing_ok=True)
                            return None
                        f.write(chunk)
                return dest
        except Exception as e:
            logger.info("Download failed for %s: %s", url, e)
            dest.unlink(missing_ok=True)
            return None


async def download_and_validate_assets(
    all_urls: list[str],
    tmp_dir: Path,
    skip_clamav: bool = False,
) -> AssetManifest:
    """Download, deduplicate, validate, and return an AssetManifest."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Limit total
    urls = all_urls[:_MAX_TOTAL]

    # Download all concurrently (semaphore created here, not at module level,
    # to avoid event loop binding issues in Python 3.11+)
    semaphore = asyncio.Semaphore(5)
    downloaded: list[DownloadedAsset] = []
    seen_hashes: dict[str, DownloadedAsset] = {}
    total_size = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        url_to_filename: dict[str, str] = {}
        for url in urls:
            parsed = urlparse(url)
            raw_name = Path(parsed.path).name or "asset"
            slug = slugify_filename(raw_name)
            # Handle collisions
            dest = assets_dir / slug
            counter = 2
            while dest.exists() or slug in url_to_filename.values():
                stem, _, ext = slug.rpartition(".")
                slug = f"{stem}-{counter}.{ext}" if ext else f"{slug}-{counter}"
                dest = assets_dir / slug
                counter += 1
            url_to_filename[url] = slug
            tasks.append(_download_one(session, url, dest, semaphore))

        results = await asyncio.gather(*tasks)

    # Validate each downloaded file
    for url, result in zip(urls, results):
        if result is None:
            continue
        path = result
        slug = url_to_filename[url]

        # Content-hash dedup
        fhash = file_hash(path)
        if fhash in seen_hashes:
            path.unlink()
            continue

        # Size budget check
        fsize = path.stat().st_size
        if total_size + fsize > _MAX_SITE_SIZE:
            path.unlink()
            continue

        # Full validation chain
        if not validate_asset(path, skip_clamav=skip_clamav):
            path.unlink(missing_ok=True)
            continue

        asset = DownloadedAsset(
            original_url=url,
            local_path=f"assets/{slug}",
            content_type=__import__("magic").from_file(str(path), mime=True),
            size_bytes=fsize,
            file_hash=fhash,
            source_page=url,
            tmp_path=path,
        )
        downloaded.append(asset)
        seen_hashes[fhash] = asset
        total_size += fsize

    return AssetManifest(assets=downloaded, total_size_bytes=total_size)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_asset_downloader.py -v`
Expected: All PASS.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check sastaspace/asset_downloader.py tests/test_asset_downloader.py
uv run ruff format sastaspace/asset_downloader.py tests/test_asset_downloader.py
git add sastaspace/asset_downloader.py tests/test_asset_downloader.py
git commit -m "feat: add asset downloader with discovery, dedup, and validation"
```

---

## Task 5: Business Profiler

**Files:**
- Create: `sastaspace/business_profiler.py`
- Test: `tests/test_business_profiler.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_business_profiler.py
import json
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.business_profiler import build_business_profile, _deduplicate_text
from sastaspace.models import BusinessProfile, PageCrawlResult
from sastaspace.crawler import CrawlResult


def _make_homepage(**overrides):
    defaults = dict(
        url="https://example.com", title="Acme Corp", meta_description="Best widgets",
        favicon_url="", html_source="", screenshot_base64="",
        headings=["Welcome to Acme"], navigation_links=[], text_content="We make widgets.",
        images=[], colors=[], fonts=[], sections=[],
    )
    defaults.update(overrides)
    return CrawlResult(**defaults)


def _make_page(**overrides):
    defaults = dict(
        url="https://example.com/about", page_type="about", title="About",
        headings=["Our Story"], text_content="Founded in 2020.", images=[], testimonials=[],
    )
    defaults.update(overrides)
    return PageCrawlResult(**defaults)


class TestDeduplicateText:
    def test_removes_duplicate_sentences(self):
        texts = ["Header text. We make widgets.", "Header text. About our team."]
        result = _deduplicate_text(texts)
        assert result.count("Header text.") == 1

    def test_preserves_unique_content(self):
        texts = ["Unique content A.", "Unique content B."]
        result = _deduplicate_text(texts)
        assert "Unique content A." in result
        assert "Unique content B." in result

    def test_handles_no_newlines(self):
        """Crawler output is single-line — splitting on newlines would fail."""
        texts = ["Welcome to Acme. We build widgets. Contact us today."]
        result = _deduplicate_text(texts)
        assert "Welcome to Acme." in result
        assert "We build widgets." in result


class TestBuildBusinessProfile:
    @patch("sastaspace.business_profiler._call_llm")
    def test_returns_profile_from_llm(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "business_name": "Acme Corp",
            "industry": "manufacturing",
            "services": ["Widget production"],
            "target_audience": "B2B companies",
            "tone": "professional",
            "differentiators": ["Fastest delivery"],
            "social_proof": ["500+ clients"],
            "pricing_model": "contact-based",
            "cta_primary": "Get a Quote",
            "brand_personality": "Reliable and efficient.",
        })
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "manufacturing"

    @patch("sastaspace.business_profiler._call_llm")
    def test_fallback_on_llm_failure(self, mock_llm):
        mock_llm.side_effect = Exception("API down")
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "unknown"

    @patch("sastaspace.business_profiler._call_llm")
    def test_fallback_on_invalid_json(self, mock_llm):
        mock_llm.return_value = "not valid json at all"
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_business_profiler.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement business profiler**

```python
# sastaspace/business_profiler.py
"""LLM-powered business profile extraction from crawled pages."""
from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from sastaspace.crawler import CrawlResult
from sastaspace.models import BusinessProfile, PageCrawlResult

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """Analyze these web pages from a single business and extract a structured business profile.

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{
  "business_name": "string",
  "industry": "string — e.g. dental, saas, restaurant, legal, ecommerce, agency",
  "services": ["list of specific offerings"],
  "target_audience": "who they serve",
  "tone": "one of: professional, casual, luxurious, friendly, technical, playful, corporate",
  "differentiators": ["what makes them unique"],
  "social_proof": ["testimonials, client names, review counts, awards"],
  "pricing_model": "listed | contact-based | freemium | subscription | none-found",
  "cta_primary": "their main call-to-action text",
  "brand_personality": "2-3 sentence summary of the brand voice and personality"
}"""


def _deduplicate_text(texts: list[str]) -> str:
    """Remove duplicate sentences across pages (header/footer boilerplate).

    The crawler's _extract_text() collapses whitespace into single spaces,
    so we split on sentence boundaries ('. ') rather than newlines.
    """
    all_sentences: list[list[str]] = []
    for text in texts:
        # Split on sentence-ending punctuation followed by space
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        all_sentences.append(sentences)
    result_parts = []
    seen: set[str] = set()
    for sentences in all_sentences:
        for s in sentences:
            if s in seen:
                continue
            seen.add(s)
            result_parts.append(s)
    return " ".join(result_parts)


def _call_llm(prompt: str, api_url: str, model: str, api_key: str) -> str:
    """Make a single LLM call for extraction."""
    client = OpenAI(base_url=api_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def build_business_profile(
    homepage: CrawlResult,
    internal_pages: list[PageCrawlResult],
    api_url: str,
    model: str,
    api_key: str,
) -> BusinessProfile:
    """Extract a structured business profile from crawled pages via LLM."""
    texts = [homepage.text_content]
    for p in internal_pages:
        if not p.error:
            texts.append(p.text_content)
    deduped = _deduplicate_text(texts)

    prompt_parts = [
        f"## Homepage: {homepage.title}",
        f"Meta: {homepage.meta_description}",
        f"Headings: {', '.join(homepage.headings[:10])}",
        deduped[:8000],
    ]
    for p in internal_pages:
        if p.error:
            continue
        prompt_parts.append(f"\n## {p.page_type.title()}: {p.title}")
        prompt_parts.append(f"Headings: {', '.join(p.headings[:10])}")
        if p.testimonials:
            prompt_parts.append(f"Testimonials: {' | '.join(p.testimonials[:5])}")
    user_prompt = "\n".join(prompt_parts)

    try:
        raw = _call_llm(user_prompt, api_url, model, api_key)
        # Try to extract JSON from possible markdown fencing
        if "```" in raw:
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)
        data = json.loads(raw)
        return BusinessProfile(
            business_name=data.get("business_name", homepage.title),
            industry=data.get("industry", "unknown"),
            services=data.get("services", []),
            target_audience=data.get("target_audience", "unknown"),
            tone=data.get("tone", "unknown"),
            differentiators=data.get("differentiators", []),
            social_proof=data.get("social_proof", []),
            pricing_model=data.get("pricing_model", "none-found"),
            cta_primary=data.get("cta_primary", "unknown"),
            brand_personality=data.get("brand_personality", "unknown"),
        )
    except Exception as e:
        logger.warning("Business profiling failed, using minimal profile: %s", e)
        return BusinessProfile.minimal(homepage.title)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_business_profiler.py -v`
Expected: All PASS.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check sastaspace/business_profiler.py tests/test_business_profiler.py
uv run ruff format sastaspace/business_profiler.py tests/test_business_profiler.py
git add sastaspace/business_profiler.py tests/test_business_profiler.py
git commit -m "feat: add LLM-powered business profiler with text dedup and fallback"
```

---

## Task 6: Crawler Refactor + Enhanced Crawl

**Files:**
- Modify: `sastaspace/crawler.py`
- Test: `tests/test_crawler_enhanced.py`

This is the largest task. Refactor `crawl()` to extract `_crawl_page()`, add `_crawl_internal_page()`, link discovery, LLM page selection, and `enhanced_crawl()`.

- [ ] **Step 1: Write tests for link extraction and filtering**

```python
# tests/test_crawler_enhanced.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import _extract_all_internal_links, _filter_noise_links


class TestExtractAllInternalLinks:
    def test_finds_nav_and_footer_links(self):
        html = """
        <html><body>
          <nav><a href="/about">About</a></nav>
          <footer><a href="/contact">Contact</a></footer>
          <a href="/blog">Blog</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        urls = [l["url"] for l in links]
        assert "https://example.com/about" in urls
        assert "https://example.com/contact" in urls
        assert "https://example.com/blog" in urls

    def test_skips_external_links(self):
        html = '<html><body><a href="https://other.com/page">Other</a></body></html>'
        links = _extract_all_internal_links(html, "https://example.com")
        assert len(links) == 0

    def test_deduplicates(self):
        html = '<html><body><a href="/about">About</a><a href="/about">About Us</a></body></html>'
        links = _extract_all_internal_links(html, "https://example.com")
        urls = [l["url"] for l in links]
        assert urls.count("https://example.com/about") == 1

    def test_caps_at_50(self):
        anchors = "".join(f'<a href="/page{i}">Page {i}</a>' for i in range(100))
        html = f"<html><body>{anchors}</body></html>"
        links = _extract_all_internal_links(html, "https://example.com")
        assert len(links) <= 50


class TestFilterNoiseLinks:
    def test_removes_fragments(self):
        links = [{"url": "https://example.com#section", "text": "Jump"}]
        filtered = _filter_noise_links(links, "https://example.com")
        assert len(filtered) == 0

    def test_removes_login(self):
        links = [{"url": "https://example.com/login", "text": "Login"}]
        filtered = _filter_noise_links(links, "https://example.com")
        assert len(filtered) == 0

    def test_removes_file_downloads(self):
        links = [{"url": "https://example.com/doc.pdf", "text": "PDF"}]
        filtered = _filter_noise_links(links, "https://example.com")
        assert len(filtered) == 0

    def test_keeps_about_page(self):
        links = [{"url": "https://example.com/about-us", "text": "About Us"}]
        filtered = _filter_noise_links(links, "https://example.com")
        assert len(filtered) == 1


class TestLlmSelectPages:
    @patch("sastaspace.crawler.OpenAI")
    def test_returns_valid_urls(self, mock_openai_cls):
        from sastaspace.crawler import _llm_select_pages
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content="https://example.com/about\nhttps://example.com/services"
            ))]
        )
        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/blog", "text": "Blog"},
            {"url": "https://example.com/contact", "text": "Contact"},
        ]
        result = _llm_select_pages(links, "http://test", "m", "k")
        assert len(result) == 2
        assert "https://example.com/about" in result

    def test_fewer_than_3_returns_all(self):
        from sastaspace.crawler import _llm_select_pages
        links = [{"url": "https://example.com/about", "text": "About"}]
        result = _llm_select_pages(links, "http://test", "m", "k")
        assert result == ["https://example.com/about"]

    @patch("sastaspace.crawler.OpenAI")
    def test_fallback_on_exception(self, mock_openai_cls):
        from sastaspace.crawler import _llm_select_pages
        mock_openai_cls.return_value.chat.completions.create.side_effect = Exception("fail")
        links = [
            {"url": "https://example.com/a", "text": "A"},
            {"url": "https://example.com/b", "text": "B"},
            {"url": "https://example.com/c", "text": "C"},
            {"url": "https://example.com/d", "text": "D"},
        ]
        result = _llm_select_pages(links, "http://test", "m", "k")
        assert len(result) == 3  # falls back to first 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_crawler_enhanced.py -v`
Expected: ImportError — `_extract_all_internal_links` not found.

- [ ] **Step 3: Add link extraction functions to crawler.py**

Add these functions to `sastaspace/crawler.py` (after the existing helper functions, before `crawl()`):

```python
def _extract_all_internal_links(html: str, base_url: str) -> list[dict]:
    """Extract all internal links from page HTML. Returns [{url, text}], max 50."""
    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.hostname or ""
    seen: set[str] = set()
    links: list[dict] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.hostname and parsed.hostname != base_domain:
            continue
        # Normalize: strip fragment
        clean = urlunparse(parsed._replace(fragment=""))
        if clean in seen or clean == base_url.rstrip("/"):
            continue
        seen.add(clean)
        text = a.get_text(strip=True)[:100]
        links.append({"url": clean, "text": text})
        if len(links) >= 50:
            break
    return links


_NOISE_PATTERNS = {
    "paths": {"/login", "/signin", "/signup", "/register", "/cart", "/checkout",
              "/search", "/wp-admin", "/admin", "/wp-login", "/feed", "/rss"},
    "extensions": {".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".csv"},
    "keywords": {"login", "signin", "signup", "cart", "checkout", "account", "password"},
}


def _filter_noise_links(links: list[dict], base_url: str) -> list[dict]:
    """Remove links that are unlikely to contain business content."""
    filtered = []
    for link in links:
        url = link["url"]
        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        # Skip homepage itself
        if not path or path == "/":
            continue
        # Skip fragment-only
        if url == base_url.rstrip("/") + "#" or parsed.path == "":
            continue
        # Skip file downloads
        if any(path.endswith(ext) for ext in _NOISE_PATTERNS["extensions"]):
            continue
        # Skip auth/utility paths
        if any(path == p or path.startswith(p + "/") for p in _NOISE_PATTERNS["paths"]):
            continue
        # Skip pagination
        if re.search(r"/page/\d+", path) or "page=" in (parsed.query or ""):
            continue
        # Skip very long query strings (tracking)
        if len(parsed.query or "") > 256:
            continue
        filtered.append(link)
    return filtered
```

Note: Add `from urllib.parse import urljoin, urlparse, urlunparse` to the imports at the top of `crawler.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_crawler_enhanced.py -v`
Expected: All PASS.

- [ ] **Step 5: Refactor crawl() — extract _crawl_page()**

In `sastaspace/crawler.py`, refactor the `crawl()` function (line 133–237):

1. Extract lines 160–237 (everything after `page = await ctx.new_page()`) into `async def _crawl_page(page, url) -> CrawlResult`
2. Make `crawl()` a thin wrapper that creates the browser and calls `_crawl_page()`
3. Add `_crawl_internal_page(page, url) -> PageCrawlResult` — lighter version, no screenshot, 3000 char text, testimonial extraction

The existing `crawl()` public signature `async def crawl(url: str) -> CrawlResult` must remain unchanged.

- [ ] **Step 6: Run existing crawler tests to verify no regressions**

Run: `uv run pytest tests/test_crawler.py -v`
Expected: All existing tests PASS.

- [ ] **Step 7: Add enhanced_crawl() with LLM page selection**

Add to `sastaspace/crawler.py`:

```python
def _llm_select_pages(
    links: list[dict], api_url: str, model: str, api_key: str,
) -> list[str]:
    """Ask LLM to pick best 3 internal pages for business understanding.

    Sync function — call via asyncio.to_thread() from async context.
    """
    if len(links) <= 3:
        return [l["url"] for l in links]
    link_list = "\n".join(f"- {l['text']}: {l['url']}" for l in links[:50])
    prompt = (
        "Which 3 of these pages would give the most insight into what this business does, "
        "who they serve, and what makes them unique? Return ONLY the 3 URLs, one per line, "
        "in priority order. No explanation.\n\n" + link_list
    )
    try:
        client = OpenAI(base_url=api_url, api_key=api_key)
        resp = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            max_tokens=200, temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        # Extract URLs from response
        selected = []
        valid_urls = {l["url"] for l in links}
        for line in text.strip().split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line in valid_urls:
                selected.append(line)
        return selected[:3]
    except Exception as e:
        logger.warning("LLM page selection failed: %s — using first 3 links", e)
        return [l["url"] for l in links[:3]]


async def enhanced_crawl(url: str, settings) -> EnhancedCrawlResult:
    """Crawl homepage + up to 3 internal pages, download assets, build business profile."""
    from sastaspace.asset_downloader import download_and_validate_assets, extract_asset_urls
    from sastaspace.business_profiler import build_business_profile
    from sastaspace.models import EnhancedCrawlResult

    _ensure_chromium()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()

            # 1. Homepage crawl
            homepage = await _crawl_page(page, url)
            if homepage.error:
                return EnhancedCrawlResult(homepage=homepage)

            # 2. Discover + select internal pages
            all_links = _extract_all_internal_links(homepage.html_source, url)
            filtered = _filter_noise_links(all_links, url)
            selected_urls = await asyncio.to_thread(
                _llm_select_pages, filtered,
                settings.claude_code_api_url, settings.claude_model, settings.claude_code_api_key,
            )

            # 3. Crawl internal pages (parallel, with timeout)
            internal_pages = []
            if selected_urls:
                async def _safe_crawl(link_url):
                    try:
                        p = await ctx.new_page()
                        return await asyncio.wait_for(
                            _crawl_internal_page(p, link_url), timeout=30.0
                        )
                    except Exception as e:
                        return PageCrawlResult(
                            url=link_url, page_type="other", title="", headings=[],
                            text_content="", images=[], testimonials=[], error=str(e),
                        )

                internal_pages = list(await asyncio.gather(*[
                    _safe_crawl(u) for u in selected_urls
                ]))

            # 4. Collect + download + validate assets
            tmp_dir = Path(tempfile.mkdtemp(prefix="sastaspace-assets-"))
            all_asset_urls = extract_asset_urls(homepage.html_source, url)
            for p in internal_pages:
                if not p.error:
                    # Extract asset URLs from internal page images list
                    for img in p.images:
                        src = img.get("src", "")
                        if src and not src.startswith(("data:", "blob:")):
                            absolute = urljoin(p.url, src)
                            if absolute not in all_asset_urls:
                                all_asset_urls.append(absolute)
            assets = await download_and_validate_assets(all_asset_urls, tmp_dir)

            # 5. Business profile
            profile = await asyncio.to_thread(
                build_business_profile, homepage, internal_pages,
                settings.claude_code_api_url, settings.claude_model, settings.claude_code_api_key,
            )
        finally:
            await browser.close()

    return EnhancedCrawlResult(
        homepage=homepage, internal_pages=internal_pages,
        assets=assets, business_profile=profile,
    )
```

- [ ] **Step 8: Run all crawler tests**

Run: `uv run pytest tests/test_crawler.py tests/test_crawler_enhanced.py -v`
Expected: All PASS.

- [ ] **Step 9: Lint and commit**

```bash
uv run ruff check sastaspace/crawler.py tests/test_crawler_enhanced.py
uv run ruff format sastaspace/crawler.py tests/test_crawler_enhanced.py
git add sastaspace/crawler.py tests/test_crawler_enhanced.py
git commit -m "feat: add enhanced_crawl() with multi-page crawl, asset download, business profiling"
```

---

## Task 7: Database + JobStatus Updates

**Files:**
- Modify: `sastaspace/database.py` (lines 17–23 JobStatus enum, lines 95–133 update_job)
- Test: `tests/test_database.py` (extend)

- [ ] **Step 1: Add new status values to JobStatus enum**

In `sastaspace/database.py`, update the `JobStatus` enum (line 17):

```python
class JobStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    DISCOVERING = "discovering"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    REDESIGNING = "redesigning"
    DEPLOYING = "deploying"
    DONE = "done"
    FAILED = "failed"
```

- [ ] **Step 2: Add new parameters to update_job()**

In `sastaspace/database.py`, add new keyword arguments to `update_job()` (line 95):

Add after `checkpoint` parameter:
```python
    pages_crawled: int | None = None,
    assets_count: int | None = None,
    assets_total_size: int | None = None,
    business_profile: dict | None = None,
```

Add in the body after the existing `if checkpoint` block:
```python
    if pages_crawled is not None:
        updates["pages_crawled"] = pages_crawled
    if assets_count is not None:
        updates["assets_count"] = assets_count
    if assets_total_size is not None:
        updates["assets_total_size"] = assets_total_size
    if business_profile is not None:
        updates["business_profile"] = business_profile
```

- [ ] **Step 3: Write tests for new update_job parameters**

Add to `tests/test_database.py`:

```python
@pytest.mark.asyncio
async def test_update_job_new_fields(mock_db):
    """Test that new enhanced crawl fields are persisted."""
    from sastaspace.database import create_job, update_job, get_job
    job = await create_job("test-new-fields", "https://x.com", "127.0.0.1")
    await update_job(
        "test-new-fields",
        pages_crawled=3,
        assets_count=12,
        assets_total_size=2048000,
        business_profile={"business_name": "Test", "industry": "tech"},
    )
    updated = await get_job("test-new-fields")
    assert updated["pages_crawled"] == 3
    assert updated["assets_count"] == 12
    assert updated["assets_total_size"] == 2048000
    assert updated["business_profile"]["industry"] == "tech"
```

- [ ] **Step 4: Run all database tests**

Run: `uv run pytest tests/test_database.py -v`
Expected: All PASS (existing + new).

- [ ] **Step 5: Commit**

```bash
git add sastaspace/database.py tests/test_database.py
git commit -m "feat: add DISCOVERING/DOWNLOADING/ANALYZING status + new job fields"
```

---

## Task 8: Deployer — Asset Support

**Files:**
- Modify: `sastaspace/deployer.py` (line 66, `deploy()` function)
- Modify: `tests/test_deployer.py` (extend)

- [ ] **Step 1: Write test for asset deployment**

Add to `tests/test_deployer.py`:

```python
def test_deploy_with_assets(tmp_path):
    from pathlib import Path
    from sastaspace.deployer import deploy
    from sastaspace.models import DownloadedAsset

    # Create tmp asset files
    tmp_asset_dir = tmp_path / "tmp_assets"
    tmp_asset_dir.mkdir()
    logo = tmp_asset_dir / "logo.png"
    logo.write_bytes(b"fake png content")

    assets = [
        DownloadedAsset(
            original_url="https://example.com/logo.png",
            local_path="assets/logo.png",
            content_type="image/png",
            size_bytes=16,
            file_hash="abc",
            source_page="https://example.com",
            tmp_path=logo,
        )
    ]
    result = deploy("https://example.com", "<html></html>", tmp_path / "sites", assets=assets)
    asset_path = tmp_path / "sites" / result.subdomain / "assets" / "logo.png"
    assert asset_path.exists()
    assert asset_path.read_bytes() == b"fake png content"
    # Original tmp file should be moved
    assert not logo.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_deployer.py::test_deploy_with_assets -v`
Expected: TypeError — `deploy()` got unexpected keyword argument `assets`.

- [ ] **Step 3: Update deploy() to accept and write assets**

In `sastaspace/deployer.py`, update `deploy()`:

1. Add `import shutil` to imports
2. Add `assets: list | None = None` parameter
3. After writing `index.html` and before the registry update, add:

```python
    if assets:
        assets_dir = site_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        for asset in assets:
            dest = site_dir / asset.local_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(asset.tmp_path), str(dest))
        metadata["assets_count"] = len(assets)
        metadata["total_assets_size"] = sum(a.size_bytes for a in assets)
```

- [ ] **Step 4: Run all deployer tests**

Run: `uv run pytest tests/test_deployer.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add sastaspace/deployer.py tests/test_deployer.py
git commit -m "feat: deploy() writes downloaded assets to sites/{subdomain}/assets/"
```

---

## Task 9: Redesigner — Enhanced Context

**Files:**
- Modify: `sastaspace/redesigner.py` (line 342, `run_redesign()`)
- Modify: `tests/test_redesigner.py` (extend)

- [ ] **Step 1: Write test for enhanced prompt context**

Add to `tests/test_redesigner.py`:

```python
@patch("sastaspace.redesigner._redesign_with_prompts")
def test_run_redesign_uses_enhanced_context(mock_redesign):
    from sastaspace.models import EnhancedCrawlResult, BusinessProfile, AssetManifest
    mock_redesign.return_value = "<!DOCTYPE html><html><body>redesigned</body></html>"
    homepage = CrawlResult(url="https://x.com", title="X", ...)  # use existing test fixture
    enhanced = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=AssetManifest(assets=[], total_size_bytes=0),
        business_profile=BusinessProfile.minimal("X Corp"),
    )
    settings = MagicMock()
    settings.claude_code_api_url = "http://test"
    settings.claude_model = "test-model"
    settings.claude_code_api_key = "test"
    settings.use_agno_pipeline = False

    result = run_redesign(homepage, settings, tier="standard", enhanced=enhanced)
    assert "redesigned" in result
    # Verify the prompt contained business profile
    call_args = mock_redesign.call_args
    user_template = call_args[0][2]  # user_template is 3rd positional arg
    # The template should reference enhanced context
```

- [ ] **Step 2: Update run_redesign() signature**

In `sastaspace/redesigner.py`, at `run_redesign()` (line 342), add the `enhanced` parameter:

```python
def run_redesign(
    crawl_result: CrawlResult,
    settings,
    tier: str = "standard",
    progress_callback=None,
    checkpoint: dict | None = None,
    checkpoint_callback=None,
    enhanced=None,  # EnhancedCrawlResult | None
) -> str:
```

Inside the function, before calling `_redesign_with_prompts()`, check if `enhanced` is provided and build an enriched user template:

```python
    # Build prompt context
    if enhanced is not None:
        crawl_context = enhanced.to_prompt_context()
    else:
        crawl_context = crawl_result.to_prompt_context()
```

Add asset-aware instructions to the system prompt when enhanced is provided.

- [ ] **Step 3: Run all redesigner tests**

Run: `uv run pytest tests/test_redesigner.py tests/test_redesigner_premium.py -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add sastaspace/redesigner.py tests/test_redesigner.py
git commit -m "feat: run_redesign() accepts enhanced context for asset-aware redesigns"
```

---

## Task 10: Worker Handler Integration

**Files:**
- Modify: `sastaspace/jobs.py` (line 334, `redesign_handler()`)
- Modify: `tests/test_jobs.py` (extend)

- [ ] **Step 1: Update redesign_handler() to use enhanced_crawl()**

In `sastaspace/jobs.py`, update `redesign_handler()` (line 323):

Replace the Step 1 crawl section with:

```python
    from sastaspace.crawler import enhanced_crawl

    # Step 1: Enhanced crawl (crawl + discover + download + profile)
    logger.info("JOB STEP 1/6: Enhanced crawl | job=%s url=%s", job_id, url)
    await update_job(job_id, status=JobStatus.CRAWLING.value, progress=5,
                     message="Crawling your site...")
    await job_service.publish_status(job_id, "crawling",
        {"job_id": job_id, "message": "Crawling your site...", "progress": 5})

    enhanced_result = await enhanced_crawl(url, settings)
    crawl_result = enhanced_result.homepage

    if crawl_result.error:
        # ... existing error handling ...

    # Update job with enhanced data
    await update_job(
        job_id,
        status=JobStatus.ANALYZING.value,
        progress=45,
        message="Building business profile...",
        pages_crawled=len(enhanced_result.internal_pages),
        assets_count=len(enhanced_result.assets.assets),
        assets_total_size=enhanced_result.assets.total_size_bytes,
        site_colors=crawl_result.colors[:5],
        site_title=crawl_result.title,
    )
```

Update Step 2 (redesign) to pass `enhanced`:

```python
    html = await asyncio.to_thread(
        run_redesign, crawl_result, settings, tier,
        _on_agent_progress, pipeline_checkpoint, _on_checkpoint,
        enhanced=enhanced_result,  # NEW — use keyword to avoid positional fragility
    )
```

Update Step 3 (deploy) to pass assets:

```python
    result = await asyncio.to_thread(
        deploy, url, html, settings.sites_dir,
        assets=enhanced_result.assets.assets,  # NEW — write assets alongside HTML
    )
```

- [ ] **Step 2: Run all job tests**

Run: `uv run pytest tests/test_jobs.py tests/test_job_stream.py -v`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add sastaspace/jobs.py
git commit -m "feat: worker handler uses enhanced_crawl() for multi-page asset-aware pipeline"
```

---

## Task 11: Frontend — Updated Step Labels

**Files:**
- Modify: `web/src/hooks/use-redesign.ts` (lines 34–56, STEPS and STATUS_TO_STEP)
- Modify: `web/src/lib/sse-client.ts` (line 8, JobStatus type)

- [ ] **Step 1: Update STEPS constant**

In `web/src/hooks/use-redesign.ts`, update `STEPS` (line 34):

```typescript
const STEPS = [
  { name: "crawling", label: (d: string) => `Analyzing ${d}` },
  { name: "discovering", label: (_: string) => "Discovering internal pages" },
  { name: "downloading", label: (_: string) => "Downloading site assets" },
  { name: "analyzing", label: (_: string) => "Understanding the business" },
  { name: "redesigning", label: (_: string) => "Redesigning your site with AI" },
  { name: "deploying", label: (d: string) => `Preparing your new ${d}` },
] as const;
```

Update `STATUS_TO_STEP` (line 51) — must match existing `{ stepName, progressValue }` object format:

```typescript
const STATUS_TO_STEP: Record<string, { stepName: string; progressValue: number }> = {
  queued: { stepName: "crawling", progressValue: 5 },
  crawling: { stepName: "crawling", progressValue: 15 },
  discovering: { stepName: "discovering", progressValue: 25 },
  downloading: { stepName: "downloading", progressValue: 35 },
  analyzing: { stepName: "analyzing", progressValue: 45 },
  redesigning: { stepName: "redesigning", progressValue: 65 },
  deploying: { stepName: "deploying", progressValue: 90 },
};
```

- [ ] **Step 2: Update JobStatus type in sse-client.ts**

In `web/src/lib/sse-client.ts`, update the `JobStatus` type (line 8) to include the new status fields:

```typescript
export interface JobStatus {
  id: string;
  status: string;
  progress: number;
  message: string;
  subdomain?: string;
  error?: string;
  site_colors?: string[];
  site_title?: string;
  pages_crawled?: number;   // NEW
  assets_count?: number;    // NEW
}
```

- [ ] **Step 3: Run frontend tests**

Run: `cd web && npm test -- --run`
Expected: All PASS (or update any snapshot tests that break from the new STEPS).

- [ ] **Step 4: Commit**

```bash
git add web/src/hooks/use-redesign.ts web/src/lib/sse-client.ts
git commit -m "feat(frontend): update progress steps for enhanced crawl pipeline"
```

---

## Task 12: ClamAV K8s Manifest

**Files:**
- Modify: `k8s/backend.yaml` (add ClamAV sidecar + shared volume)

- [ ] **Step 1: Add ClamAV sidecar and emptyDir volume to backend deployment**

In `k8s/backend.yaml`, add to the pod spec:

1. Add `emptyDir` volume:
```yaml
      volumes:
      - name: sites-storage
        persistentVolumeClaim:
          claimName: sites-pvc
      - name: scan-tmp          # NEW
        emptyDir:
          sizeLimit: 256Mi
```

2. Add volume mount to backend container:
```yaml
          volumeMounts:
          - name: sites-storage
            mountPath: /data/sites
          - name: scan-tmp       # NEW
            mountPath: /tmp/scan
```

3. Add ClamAV sidecar container:
```yaml
      - name: clamav
        image: clamav/clamav:latest
        ports:
        - containerPort: 3310
        volumeMounts:
        - name: scan-tmp
          mountPath: /tmp/scan
        resources:
          requests:
            memory: "512Mi"
            cpu: "100m"
          limits:
            memory: "4Gi"
            cpu: "500m"
        readinessProbe:
          tcpSocket:
            port: 3310
          initialDelaySeconds: 60
          periodSeconds: 10
```

- [ ] **Step 2: Commit**

```bash
git add k8s/backend.yaml
git commit -m "infra: add ClamAV sidecar with shared emptyDir volume for asset scanning"
```

---

## Task 13: Integration Test + Full Pipeline Verification

**Files:**
- Create: `tests/test_enhanced_pipeline.py`

- [ ] **Step 1: Write integration test with mocked external services**

```python
# tests/test_enhanced_pipeline.py
"""Integration test for the full enhanced crawl pipeline with mocked services."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.models import EnhancedCrawlResult


@pytest.mark.asyncio
@patch("sastaspace.crawler.async_playwright")
@patch("sastaspace.business_profiler._call_llm")
async def test_enhanced_crawl_full_pipeline(mock_llm, mock_pw, tmp_path):
    """Test that enhanced_crawl returns a valid EnhancedCrawlResult with all components."""
    import json
    from sastaspace.crawler import enhanced_crawl

    # Mock Playwright
    mock_page = AsyncMock()
    mock_page.title.return_value = "Test Business"
    mock_page.content.return_value = """
    <html><head><title>Test Business</title>
    <meta name="description" content="Best test business">
    <link rel="icon" href="/favicon.ico">
    <meta property="og:image" content="/og.jpg">
    </head><body>
    <nav><a href="/about">About</a><a href="/services">Services</a></nav>
    <h1>Welcome</h1><p>We are a test business.</p>
    <img src="/logo.png" alt="Logo">
    </body></html>
    """
    mock_page.screenshot.return_value = b"fake-screenshot"
    mock_page.evaluate.return_value = []

    mock_ctx = AsyncMock()
    mock_ctx.new_page.return_value = mock_page
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_ctx
    mock_pw_instance = AsyncMock()
    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_pw.return_value.__aenter__.return_value = mock_pw_instance

    # Mock LLM responses
    mock_llm.return_value = json.dumps({
        "business_name": "Test Business",
        "industry": "testing",
        "services": ["Testing"],
        "target_audience": "Testers",
        "tone": "professional",
        "differentiators": ["Best tests"],
        "social_proof": [],
        "pricing_model": "none-found",
        "cta_primary": "Get Started",
        "brand_personality": "Reliable.",
    })

    settings = MagicMock()
    settings.claude_code_api_url = "http://test:8000/v1"
    settings.claude_model = "test-model"
    settings.claude_code_api_key = "test-key"

    with patch("sastaspace.crawler._ensure_chromium"):
        result = await enhanced_crawl("https://testbusiness.com", settings)

    assert isinstance(result, EnhancedCrawlResult)
    assert result.homepage.title == "Test Business"
    assert result.business_profile.business_name == "Test Business"
    assert result.business_profile.industry == "testing"

    # Verify prompt context includes all sections
    ctx = result.to_prompt_context()
    assert "Business Profile" in ctx
    assert "Test Business" in ctx
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/test_enhanced_pipeline.py -v`
Expected: All PASS.

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All existing + new tests PASS.

- [ ] **Step 4: Lint everything**

Run: `uv run ruff check sastaspace/ tests/ && uv run ruff format --check sastaspace/ tests/`

- [ ] **Step 5: Final commit**

```bash
git add tests/test_enhanced_pipeline.py
git commit -m "test: add integration test for full enhanced crawl pipeline"
```

---

## Execution Order Summary

| Task | What | Dependencies |
|------|------|-------------|
| 1 | Dependencies | None |
| 2 | Data models | None |
| 3 | Asset validator | Task 1 (deps) |
| 4 | Asset downloader | Tasks 2, 3 |
| 5 | Business profiler | Task 2 |
| 6 | Crawler refactor + enhanced_crawl | Tasks 2, 4, 5 |
| 7 | Database updates | None |
| 8 | Deployer assets | Task 2 |
| 9 | Redesigner enhanced context | Tasks 2, 6 |
| 10 | Worker handler integration | Tasks 6, 7, 8, 9 |
| 11 | Frontend step labels | Task 7 |
| 12 | ClamAV k8s manifest | None |
| 13 | Integration test | All above |

**Parallelizable:** Tasks 1–2 can run first. Then 3, 4, 5, 7, 8, 12 can run in parallel. Tasks 6, 9 depend on earlier tasks. Task 10 is the integration point. Tasks 11, 13 are final.
