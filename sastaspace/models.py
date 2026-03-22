# sastaspace/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PageCrawlResult:
    url: str
    page_type: str = "other"  # "about", "services", "portfolio", "other"
    title: str = ""
    headings: list[str] = field(default_factory=list)
    text_content: str = ""  # 3000 chars max
    images: list[dict] = field(default_factory=list)
    testimonials: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class DownloadedAsset:
    original_url: str
    local_path: str  # relative: "assets/logo.png"
    content_type: str  # "image/png", "image/svg+xml", etc.
    size_bytes: int
    file_hash: str  # SHA-256 for content deduplication
    source_page: str  # which page it came from
    tmp_path: Path = field(default_factory=lambda: Path("."))


@dataclass
class AssetManifest:
    assets: list[DownloadedAsset] = field(default_factory=list)
    total_size_bytes: int = 0

    def to_prompt_context(self, max_assets: int = 15) -> str:
        """Renders as markdown table for LLM consumption."""
        if not self.assets:
            return (
                "No downloadable assets found. Use CSS gradients, solid colors, "
                "and geometric shapes for visual interest. Do not reference external image URLs."
            )

        # Priority: logo/favicon first, then by size descending
        def sort_key(a: DownloadedAsset) -> tuple[int, int]:
            is_priority = "logo" in a.local_path.lower() or "favicon" in a.local_path.lower()
            return (0 if is_priority else 1, -a.size_bytes)

        sorted_assets = sorted(self.assets, key=sort_key)[:max_assets]

        lines = [
            "## Available Assets",
            "Use these local paths in your HTML. Do NOT use placeholder images.",
            "",
            "| Local Path | Content Type | Size |",
            "|---|---|---|",
        ]
        for a in sorted_assets:
            size_kb = a.size_bytes // 1024
            lines.append(f"| {a.local_path} | {a.content_type} | {size_kb}KB |")
        return "\n".join(lines)


@dataclass
class BusinessProfile:
    business_name: str = "Unknown"
    industry: str = "unknown"
    services: list[str] = field(default_factory=list)
    target_audience: str = "unknown"
    tone: str = "professional"
    differentiators: list[str] = field(default_factory=list)
    social_proof: list[str] = field(default_factory=list)
    pricing_model: str = "none-found"
    cta_primary: str = ""
    brand_personality: str = ""


@dataclass
class EnhancedCrawlResult:
    homepage: object  # CrawlResult — avoid circular import
    internal_pages: list[PageCrawlResult] = field(default_factory=list)
    assets: AssetManifest = field(default_factory=AssetManifest)
    business_profile: BusinessProfile = field(default_factory=BusinessProfile)

    def to_prompt_context(self) -> str:
        """Combines everything into structured LLM prompt."""
        sections = []

        # Business profile
        bp = self.business_profile
        sections.append(
            f"## Business Profile\n"
            f"- **Business:** {bp.business_name} — {bp.industry}\n"
            f"- **Services:** {', '.join(bp.services) if bp.services else 'unknown'}\n"
            f"- **Audience:** {bp.target_audience}\n"
            f"- **Tone:** {bp.tone}\n"
            f"- **Differentiators:** "
            f"{', '.join(bp.differentiators) if bp.differentiators else 'none found'}\n"
            f"- **Primary CTA:** {bp.cta_primary or 'none found'}"
        )

        # Asset manifest
        sections.append(self.assets.to_prompt_context())

        # Homepage crawl data
        if hasattr(self.homepage, "to_prompt_context"):
            sections.append("## Original Website Data\n" + self.homepage.to_prompt_context())

        # Internal pages
        for page in self.internal_pages:
            if not page.error:
                page_section = f"## Internal Page: {page.title or page.url}\n"
                if page.headings:
                    page_section += "Headings: " + ", ".join(page.headings[:5]) + "\n"
                if page.text_content:
                    page_section += page.text_content[:1000]
                sections.append(page_section)

        return "\n\n".join(sections)
