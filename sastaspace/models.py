# sastaspace/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sastaspace.crawler import CrawlResult


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
    file_hash: str  # SHA-256
    source_page: str  # which page it came from
    tmp_path: Path = field(default_factory=lambda: Path())


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
        lines = [
            "## Available Assets",
            "Use these local paths in your HTML. "
            "Do NOT use placeholder images or external stock photos.\n",
            "| Local Path | Content Type | Size |",
            "|---|---|---|",
        ]
        for asset in self.assets[:max_assets]:
            size_kb = asset.size_bytes // 1024
            lines.append(f"| {asset.local_path} | {asset.content_type} | {size_kb}KB |")
        return "\n".join(lines)


@dataclass
class BusinessProfile:
    business_name: str = "unknown"
    industry: str = "unknown"
    services: list[str] = field(default_factory=list)
    target_audience: str = "unknown"
    tone: str = "unknown"
    differentiators: list[str] = field(default_factory=list)
    social_proof: list[str] = field(default_factory=list)
    pricing_model: str = "none-found"
    cta_primary: str = "unknown"
    brand_personality: str = "unknown"

    def to_prompt_context(self) -> str:
        lines = ["## Business Profile"]
        lines.append(f"- **Business:** {self.business_name} — {self.industry}")
        if self.services:
            lines.append(f"- **Services:** {', '.join(self.services)}")
        lines.append(f"- **Audience:** {self.target_audience}")
        lines.append(f"- **Tone:** {self.tone}")
        if self.differentiators:
            lines.append(f"- **Differentiators:** {', '.join(self.differentiators)}")
        if self.social_proof:
            lines.append(f"- **Social proof:** {', '.join(self.social_proof)}")
        lines.append(f"- **Primary CTA:** {self.cta_primary}")
        lines.append(f"- **Brand personality:** {self.brand_personality}")
        return "\n".join(lines)


@dataclass
class EnhancedCrawlResult:
    homepage: CrawlResult
    internal_pages: list[PageCrawlResult] = field(default_factory=list)
    assets: AssetManifest = field(default_factory=AssetManifest)
    business_profile: BusinessProfile = field(default_factory=BusinessProfile)

    def to_prompt_context(self) -> str:
        """Combines everything into structured LLM prompt."""
        sections = []

        # Business profile
        sections.append(self.business_profile.to_prompt_context())

        # Asset manifest
        sections.append(self.assets.to_prompt_context())

        # Homepage crawl data
        sections.append(self.homepage.to_prompt_context())

        # Internal pages summary
        if self.internal_pages:
            pages_lines = ["## Internal Pages"]
            for page in self.internal_pages:
                if not page.error:
                    pages_lines.append(f"\n### {page.title} ({page.page_type})")
                    pages_lines.append(f"URL: {page.url}")
                    if page.headings:
                        pages_lines.append("Headings: " + ", ".join(page.headings[:5]))
                    if page.text_content:
                        pages_lines.append(page.text_content[:1000])
            sections.append("\n".join(pages_lines))

        return "\n\n".join(sections)
