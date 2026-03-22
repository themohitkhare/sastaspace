# sastaspace/models.py
"""Enhanced crawl pipeline data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageCrawlResult:
    """Lightweight crawl result for internal (non-homepage) pages."""

    url: str
    title: str
    headings: list[str] = field(default_factory=list)
    text_content: str = ""
    navigation_links: list[dict] = field(default_factory=list)
    error: str = ""

    def to_prompt_context(self) -> str:
        lines = [
            f"## Page Title\n{self.title}",
            f"## URL\n{self.url}",
        ]
        if self.headings:
            lines.append("## Headings\n" + "\n".join(f"- {h}" for h in self.headings))
        if self.navigation_links:
            nav = "\n".join(f"- {n['text']} → {n['href']}" for n in self.navigation_links)
            lines.append(f"## Navigation\n{nav}")
        if self.text_content:
            lines.append(f"## Main Text Content\n{self.text_content[:4999]}")
        return "\n\n".join(lines)


@dataclass
class DownloadedAsset:
    """A single downloaded asset (image, font, CSS, etc.)."""

    original_url: str
    local_path: str
    asset_type: str
    size_bytes: int
    is_logo: bool = False
    is_favicon: bool = False


@dataclass
class AssetManifest:
    """Collection of all downloaded assets for a site."""

    assets: list[DownloadedAsset] = field(default_factory=list)

    def to_prompt_context(self, max_assets: int = 15) -> str:
        if not self.assets:
            return "## Downloaded Assets\nNo downloadable assets found."

        # Prioritize: logos first, favicons second, then by size descending
        def sort_key(a: DownloadedAsset) -> tuple[int, int]:
            priority = 0 if a.is_logo else (1 if a.is_favicon else 2)
            return (priority, -a.size_bytes)

        sorted_assets = sorted(self.assets, key=sort_key)
        selected = sorted_assets[:max_assets]

        lines = ["## Downloaded Assets"]
        for a in selected:
            tags = []
            if a.is_logo:
                tags.append("LOGO")
            if a.is_favicon:
                tags.append("FAVICON")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- {a.original_url} ({a.asset_type}, {a.size_bytes} bytes){tag_str}")
        return "\n".join(lines)


@dataclass
class BusinessProfile:
    """Extracted or inferred business information."""

    business_name: str
    industry: str = "unknown"
    description: str = "unknown"
    target_audience: str = "unknown"
    brand_voice: str = "unknown"
    primary_colors: list[str] = field(default_factory=list)
    contact_email: str = "unknown"
    phone: str = "unknown"
    address: str = "unknown"

    @classmethod
    def minimal(cls, business_name: str) -> BusinessProfile:
        """Create a profile with all fields set to 'unknown'."""
        return cls(business_name=business_name)

    def to_prompt_context(self) -> str:
        lines = [
            "## Business Profile",
            f"- **Name:** {self.business_name}",
            f"- **Industry:** {self.industry}",
            f"- **Description:** {self.description}",
            f"- **Target Audience:** {self.target_audience}",
            f"- **Brand Voice:** {self.brand_voice}",
            f"- **Contact Email:** {self.contact_email}",
            f"- **Phone:** {self.phone}",
            f"- **Address:** {self.address}",
        ]
        if self.primary_colors:
            lines.append(f"- **Primary Colors:** {', '.join(self.primary_colors)}")
        return "\n".join(lines)


@dataclass
class EnhancedCrawlResult:
    """Full enhanced crawl result combining homepage, internal pages, assets, and profile."""

    homepage: object  # CrawlResult — typed as object to avoid circular import
    internal_pages: list[PageCrawlResult] = field(default_factory=list)
    asset_manifest: AssetManifest = field(default_factory=AssetManifest)
    business_profile: BusinessProfile = field(default_factory=lambda: BusinessProfile.minimal(""))

    def to_prompt_context(self) -> str:
        sections = []

        # Business profile
        sections.append(self.business_profile.to_prompt_context())

        # Asset manifest
        sections.append(self.asset_manifest.to_prompt_context())

        # Homepage crawl context
        if hasattr(self.homepage, "to_prompt_context"):
            sections.append("# Homepage\n" + self.homepage.to_prompt_context())

        # Internal pages
        if self.internal_pages:
            sections.append("# Internal Pages")
            for page in self.internal_pages:
                sections.append(page.to_prompt_context())

        return "\n\n".join(sections)
