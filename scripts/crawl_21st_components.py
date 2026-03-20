#!/usr/bin/env python3
"""
Crawl ALL components from 21st.dev via tRPC API and save to components/.

Usage:
    python scripts/crawl_21st_components.py

Flow:
  1. For each category tag, call the demos.list tRPC endpoint (paginated)
  2. Collect unique (author_username, component_slug) pairs
  3. Fetch each from https://21st.dev/r/{author}/{slug} (shadcn registry format)
  4. Save as components/{author}__{slug}.json
  5. Write components/index.json
"""
from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

import httpx

# All category tag slugs from 21st.dev/community/components
CATEGORIES = {
    # Marketing Blocks
    "announcement": "Marketing Blocks",
    "background": "Marketing Blocks",
    "border": "Marketing Blocks",
    "call-to-action": "Marketing Blocks",
    "clients": "Marketing Blocks",
    "comparison": "Marketing Blocks",
    "dock": "Marketing Blocks",
    "features": "Marketing Blocks",
    "footer": "Marketing Blocks",
    "hero": "Marketing Blocks",
    "hook": "Marketing Blocks",
    "image": "Marketing Blocks",
    "map": "Marketing Blocks",
    "navbar-navigation": "Marketing Blocks",
    "pricing-section": "Marketing Blocks",
    "scroll-area": "Marketing Blocks",
    "shader": "Marketing Blocks",
    "testimonials": "Marketing Blocks",
    "text": "Marketing Blocks",
    "video": "Marketing Blocks",
    # UI Components
    "accordion": "UI Components",
    "ai-chat": "UI Components",
    "alert": "UI Components",
    "avatar": "UI Components",
    "badge": "UI Components",
    "button": "UI Components",
    "calendar": "UI Components",
    "card": "UI Components",
    "carousel": "UI Components",
    "checkbox": "UI Components",
    "date-picker": "UI Components",
    "modal-dialog": "UI Components",
    "dropdown": "UI Components",
    "empty-state": "UI Components",
    "file-tree": "UI Components",
    "upload-download": "UI Components",
    "form": "UI Components",
    "icons": "UI Components",
    "input": "UI Components",
    "link": "UI Components",
    "menu": "UI Components",
    "notification": "UI Components",
    "number": "UI Components",
    "pagination": "UI Components",
    "popover": "UI Components",
    "radio-group": "UI Components",
    "select": "UI Components",
    "sidebar": "UI Components",
    "sign-in": "UI Components",
    "registration-signup": "UI Components",
    "slider": "UI Components",
    "spinner-loader": "UI Components",
    "table": "UI Components",
    "tabs": "UI Components",
    "chip-tag": "UI Components",
    "textarea": "UI Components",
    "toast": "UI Components",
    "toggle": "UI Components",
    "tooltip": "UI Components",
}

TRPC_BASE = "https://21st.dev/api/trpc/demos.list"
REGISTRY_BASE = "https://21st.dev/r"
OUT_DIR = Path(__file__).parent.parent / "components"
OUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "sastaspace-crawler/1.0",
    "Accept": "application/json",
}


def list_components(client: httpx.Client, tag_slug: str) -> list[dict]:
    """Fetch all components for a given tag via tRPC, handling pagination."""
    items = []
    cursor = None

    while True:
        payload: dict = {
            "sortBy": "recommended",
            "tagSlug": tag_slug,
            "limit": 200,
            "includePrivate": False,
            "direction": "forward",
        }
        if cursor is not None:
            payload["cursor"] = cursor

        input_str = json.dumps({"0": {"json": payload}})
        url = f"{TRPC_BASE}?batch=1&input={urllib.parse.quote(input_str)}"

        try:
            resp = client.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            result = data[0]["result"]["data"]["json"]
            batch = result.get("items", [])
            items.extend(batch)

            next_cursor = result.get("nextCursor")
            if not next_cursor or len(batch) == 0:
                break
            cursor = next_cursor
            time.sleep(0.2)

        except Exception as e:
            print(f"    ERROR listing {tag_slug}: {e}")
            break

    return items


def extract_key(item: dict) -> tuple[str, str] | None:
    """Extract (username, component_slug) from a list item."""
    user = item.get("user_data") or {}
    comp = item.get("component_data") or {}
    username = user.get("username") or user.get("display_username")
    slug = comp.get("component_slug")
    if not username or not slug:
        return None
    return (username, slug)


def fetch_registry(client: httpx.Client, username: str, slug: str) -> dict | None:
    """Fetch component from shadcn registry endpoint."""
    url = f"{REGISTRY_BASE}/{username}/{slug}"
    try:
        resp = client.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    FAILED registry {username}/{slug}: {e}")
        return None


def build_index() -> None:
    index = []
    for f in sorted(OUT_DIR.glob("*.json")):
        if f.name == "index.json":
            continue
        try:
            d = json.loads(f.read_text())
            meta = d.get("_meta", {})
            index.append({
                "file": f.name,
                "name": d.get("name", ""),
                "title": d.get("title", ""),
                "description": d.get("description", ""),
                "author": meta.get("author", ""),
                "category": meta.get("category", ""),
                "category_group": meta.get("category_group", ""),
                "registry_url": meta.get("registry_url", ""),
                "dependencies": d.get("dependencies", []),
                "files": [fi.get("path", "") for fi in d.get("files", [])],
            })
        except Exception:
            pass

    index_file = OUT_DIR / "index.json"
    index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"\nIndex: {len(index)} components → {index_file}")


def main() -> None:
    # Collect unique (username, slug) → categories mapping
    component_map: dict[tuple[str, str], dict] = {}  # key → metadata

    with httpx.Client(headers=HEADERS) as client:
        for tag_slug, group in CATEGORIES.items():
            print(f"\n[{group}] {tag_slug} ...")
            items = list_components(client, tag_slug)
            print(f"  found {len(items)} demos")

            for item in items:
                key = extract_key(item)
                if not key:
                    continue
                username, slug = key
                if key not in component_map:
                    comp = item.get("component_data", {})
                    component_map[key] = {
                        "author": username,
                        "slug": slug,
                        "title": comp.get("name", slug),
                        "description": comp.get("description", ""),
                        "category": tag_slug,
                        "category_group": group,
                        "downloads": comp.get("downloads_count", 0),
                        "likes": comp.get("likes_count", 0),
                    }

        print(f"\n\nTotal unique components: {len(component_map)}")
        print("Fetching registry entries...\n")

        saved = 0
        failed = 0
        skipped = 0

        for (username, slug), meta in component_map.items():
            out_file = OUT_DIR / f"{username}__{slug}.json"

            if out_file.exists():
                # Update metadata on existing file if missing _meta
                try:
                    existing = json.loads(out_file.read_text())
                    if "_meta" not in existing:
                        existing["_meta"] = {
                            "author": username,
                            "slug": slug,
                            "registry_url": f"{REGISTRY_BASE}/{username}/{slug}",
                            **meta,
                        }
                        out_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
                except Exception:
                    pass
                skipped += 1
                continue

            print(f"  fetching {username}/{slug} ...")
            data = fetch_registry(client, username, slug)

            if data:
                data["_meta"] = {
                    "author": username,
                    "slug": slug,
                    "registry_url": f"{REGISTRY_BASE}/{username}/{slug}",
                    **meta,
                }
                out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                saved += 1
            else:
                failed += 1

            time.sleep(0.25)

    print(f"\nDone. {saved} new, {skipped} already existed, {failed} failed.")
    build_index()


if __name__ == "__main__":
    main()
