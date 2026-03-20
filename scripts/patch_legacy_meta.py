#!/usr/bin/env python3
"""Patch _source-only files with proper _meta including category info."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent / "components"
REGISTRY_BASE = "https://21st.dev/r"

# Manual category assignment for the 36 legacy featured files
MANUAL_CATEGORIES = {
    "Kain0127__particle-text-effect": ("text", "Marketing Blocks"),
    "Kain0127__spiral-animation": ("background", "Marketing Blocks"),
    "Northstrix__playing-card": ("card", "UI Components"),
    "aceternity__code-block": ("text", "Marketing Blocks"),
    "aliimam__highlighter": ("text", "Marketing Blocks"),
    "aliimam__liquid-glass-button": ("button", "UI Components"),
    "aliimam__shader-animation": ("shader", "Marketing Blocks"),
    "aliimam__shader-lines": ("shader", "Marketing Blocks"),
    "aliimam__web-gl-shader": ("shader", "Marketing Blocks"),
    "andrewlu0__filters": ("dropdown", "UI Components"),
    "efferd__testimonials-columns-1": ("testimonials", "Marketing Blocks"),
    "hextaui__toolbar": ("menu", "UI Components"),
    "magicui__animated-beam": ("background", "Marketing Blocks"),
    "magicui__animated-shiny-text": ("text", "Marketing Blocks"),
    "magicui__globe": ("map", "Marketing Blocks"),
    "magicui__hero-video-dialog": ("hero", "Marketing Blocks"),
    "magicui__interactive-hover-button": ("button", "UI Components"),
    "magicui__rainbow-button": ("button", "UI Components"),
    "magicui__shimmer-button": ("button", "UI Components"),
    "magicui__shine-border": ("border", "Marketing Blocks"),
    "magicui__sparkles-text": ("text", "Marketing Blocks"),
    "magicui__text-reveal": ("text", "Marketing Blocks"),
    "motion-primitives__animated-tabs": ("tabs", "UI Components"),
    "motion-primitives__text-shimmer": ("text", "Marketing Blocks"),
    "motion-primitives__transition-panel": ("modal-dialog", "UI Components"),
    "paceui__dot-loader": ("spinner-loader", "UI Components"),
    "ravikatiyar__animated-shader-hero": ("shader", "Marketing Blocks"),
    "reuno-ui__ai-input": ("input", "UI Components"),
    "serafim__gradient-button": ("button", "UI Components"),
    "serafim__splite": ("text", "Marketing Blocks"),
    "serafim__testimonials-with-marquee": ("testimonials", "Marketing Blocks"),
    "tailark__hero-section-9": ("hero", "Marketing Blocks"),
    "thanh__animated-shader-background": ("shader", "Marketing Blocks"),
    "thanh__shader-background": ("shader", "Marketing Blocks"),
    "ui-layouts__pricing-section-4": ("pricing-section", "Marketing Blocks"),
    "ui-layouts__sticky-scroll": ("scroll-area", "Marketing Blocks"),
}

patched = 0
for json_file in ROOT.glob("*.json"):
    if json_file.name == "index.json":
        continue
    stem = json_file.stem
    if stem not in MANUAL_CATEGORIES:
        continue

    category, group = MANUAL_CATEGORIES[stem]
    parts = stem.split("__", 1)
    author = parts[0] if len(parts) == 2 else stem
    slug = parts[1] if len(parts) == 2 else stem

    data = json.loads(json_file.read_text())
    if "_meta" not in data:
        src = data.get("_source", {})
        data["_meta"] = {
            "author": author,
            "slug": slug,
            "registry_url": f"{REGISTRY_BASE}/{author}/{slug}",
            "title": src.get("name", slug),
            "description": "",
            "category": category,
            "category_group": group,
        }
        json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        patched += 1
        print(f"  patched {json_file.name} → {group}/{category}")

print(f"\nPatched {patched} files.")
