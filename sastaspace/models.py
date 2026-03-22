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
            "Use these local paths in your HTML."
            " Do NOT use placeholder images or external stock photos.",
            "If an asset fits a section, use it."
            " If none fit, use CSS gradients or solid colors instead.",
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
