# sastaspace/swarm/stitcher.py
"""Deterministic page assembly from section fragments."""

from __future__ import annotations

import re

from sastaspace.swarm.schemas import ColorPalette, SectionFragment


def _extract_font_name(font_stack: str) -> str:
    match = re.match(r"['\"]?([^'\",:]+)", font_stack.strip())
    return match.group(1).strip() if match else ""


def _google_fonts_import(palette: ColorPalette) -> str:
    fonts = set()
    for font_stack in (palette.headline_font, palette.body_font):
        name = _extract_font_name(font_stack)
        if name and name.lower() not in ("sans-serif", "serif", "monospace", "arial", "helvetica"):
            fonts.add(name.replace(" ", "+"))
    if not fonts:
        return ""
    families = "&".join(f"family={f}:wght@300;400;500;600;700" for f in sorted(fonts))
    return f'@import url("https://fonts.googleapis.com/css2?{families}&display=swap");'


def stitch_page(
    fragments: list[SectionFragment],
    palette: ColorPalette,
    title: str,
) -> str:
    fonts_import = _google_fonts_import(palette)

    section_css_parts = []
    for frag in fragments:
        if frag.css.strip():
            section_css_parts.append(f"/* {frag.section_name} */\n{frag.css}")
    section_css = "\n\n".join(section_css_parts)

    section_js_parts = []
    for frag in fragments:
        if frag.js.strip():
            section_js_parts.append(f"// {frag.section_name}\n{frag.js}")
    section_js = "\n\n".join(section_js_parts)

    body_html = "\n\n".join(frag.html for frag in fragments)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    {fonts_import}

    :root {{
      --color-primary: {palette.primary};
      --color-secondary: {palette.secondary};
      --color-accent: {palette.accent};
      --color-background: {palette.background};
      --color-text: {palette.text};
      --font-headline: {palette.headline_font};
      --font-body: {palette.body_font};
      --radius: {palette.roundness};
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: var(--font-body);
      color: var(--color-text);
      background: var(--color-background);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}
    h1, h2, h3, h4, h5, h6 {{ font-family: var(--font-headline); line-height: 1.2; }}
    img {{ max-width: 100%; height: auto; display: block; }}
    a {{ color: var(--color-accent); text-decoration: none; }}

    {section_css}
  </style>
</head>
<body>
  {body_html}
  {f"<script>{section_js}</script>" if section_js else ""}
</body>
</html>"""
