# sastaspace/deployer.py
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class DeployResult:
    subdomain: str
    index_path: Path
    sites_dir: Path


def derive_subdomain(url: str) -> str:
    """
    Derive a filesystem-safe subdomain slug from a URL.

    https://www.acme-corp.co.uk/shop -> acme-corp-co-uk
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or url

    if hostname.startswith("www."):
        hostname = hostname[4:]

    slug = re.sub(r"[^a-z0-9]+", "-", hostname.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug[:50]


def _unique_subdomain(base: str, sites_dir: Path) -> str:
    """Return `base` if available, else `base--2`, `base--3`, ..."""
    candidate = base
    counter = 2
    while (sites_dir / candidate).exists():
        candidate = f"{base}--{counter}"
        counter += 1
    return candidate


def load_registry(sites_dir: Path) -> list[dict]:
    """Load the _registry.json or return empty list."""
    registry_path = sites_dir / "_registry.json"
    if not registry_path.exists():
        return []
    try:
        return json.loads(registry_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_registry(sites_dir: Path, registry: list[dict]) -> None:
    """Atomically write _registry.json via write-then-rename."""
    tmp_path = sites_dir / "_registry.json.tmp"
    tmp_path.write_text(json.dumps(registry, indent=2))
    os.replace(tmp_path, sites_dir / "_registry.json")


def deploy(
    url: str,
    html: str,
    sites_dir: Path,
    subdomain: str | None = None,
    assets: list | None = None,
) -> DeployResult:
    """
    Write redesigned HTML to sites/{subdomain}/ and update registry.

    When assets is provided, creates an assets/ subdirectory and moves
    validated files from their tmp_path to the final location.

    Returns DeployResult with final subdomain and path.
    """
    sites_dir.mkdir(parents=True, exist_ok=True)

    base = subdomain if subdomain else derive_subdomain(url)
    final_subdomain = _unique_subdomain(base, sites_dir)

    site_dir = sites_dir / final_subdomain
    site_dir.mkdir(parents=True, exist_ok=True)

    index_path = site_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")

    metadata = {
        "subdomain": final_subdomain,
        "original_url": url,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "deployed",
    }

    # Deploy assets if provided
    if assets:
        assets_dir = site_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        total_assets_size = 0
        for asset in assets:
            dest = site_dir / asset.local_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if asset.tmp_path and asset.tmp_path.exists():
                shutil.move(str(asset.tmp_path), str(dest))
            total_assets_size += asset.size_bytes
        metadata["assets_count"] = len(assets)
        metadata["total_assets_size"] = total_assets_size

    (site_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    registry = load_registry(sites_dir)
    registry = [e for e in registry if e.get("subdomain") != final_subdomain]
    registry.append(metadata)
    save_registry(sites_dir, registry)

    return DeployResult(subdomain=final_subdomain, index_path=index_path, sites_dir=sites_dir)
