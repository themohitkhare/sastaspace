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


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically via write-to-temp + os.replace."""
    tmp_path = path.parent / f"{path.name}.tmp"
    tmp_path.write_text(content, encoding=encoding)
    os.replace(tmp_path, path)


def _deploy_build_output(build_dir: Path, site_dir: Path) -> None:
    """Copy all files from a Vite build output directory into the site directory."""
    for item in build_dir.iterdir():
        dest = site_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def _deploy_assets(assets: list, site_dir: Path) -> None:
    """Move crawled asset files into the site directory."""
    for asset in assets:
        dest = site_dir / asset.local_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(asset.tmp_path), str(dest))


def _build_metadata(
    final_subdomain: str, url: str, build_dir: Path | None, assets: list | None
) -> dict:
    """Build the metadata dict for a deployed site."""
    metadata = {
        "subdomain": final_subdomain,
        "original_url": url,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "deployed",
        "build_type": "react" if build_dir else "html",
    }
    if assets:
        metadata["assets_count"] = len(assets)
        metadata["total_assets_size"] = sum(a.size_bytes for a in assets)
    return metadata


def _update_registry(sites_dir: Path, metadata: dict) -> None:
    """Append metadata to the site registry, replacing any existing entry for the subdomain."""
    registry = load_registry(sites_dir)
    registry = [e for e in registry if e.get("subdomain") != metadata["subdomain"]]
    registry.append(metadata)
    save_registry(sites_dir, registry)


def deploy(
    url: str,
    html: str,
    sites_dir: Path,
    subdomain: str | None = None,
    assets: list | None = None,
    build_dir: Path | None = None,
) -> DeployResult:
    """
    Write redesigned HTML to sites/{subdomain}/ and update registry.

    Args:
        url: Original website URL.
        html: The redesigned HTML string (index.html content).
        sites_dir: Root sites directory.
        subdomain: Optional pre-determined subdomain slug.
        assets: Optional crawled asset files to deploy alongside.
        build_dir: Optional Vite build output directory. When provided, all files
            from this directory are copied to the site dir (JS/CSS bundles, etc.)
            instead of writing just the HTML string.

    Returns DeployResult with final subdomain and path.
    """
    sites_dir.mkdir(parents=True, exist_ok=True)

    base = subdomain if subdomain else derive_subdomain(url)
    final_subdomain = _unique_subdomain(base, sites_dir)

    site_dir = sites_dir / final_subdomain
    site_dir.mkdir(parents=True, exist_ok=True)

    if build_dir and build_dir.exists():
        _deploy_build_output(build_dir, site_dir)
    else:
        _atomic_write(site_dir / "index.html", html)
    index_path = site_dir / "index.html"

    if assets:
        _deploy_assets(assets, site_dir)

    metadata = _build_metadata(final_subdomain, url, build_dir, assets)
    _atomic_write(site_dir / "metadata.json", json.dumps(metadata, indent=2))
    _update_registry(sites_dir, metadata)

    return DeployResult(subdomain=final_subdomain, index_path=index_path, sites_dir=sites_dir)
