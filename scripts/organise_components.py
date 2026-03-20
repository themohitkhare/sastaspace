#!/usr/bin/env python3
"""
Reorganise components/ into category subfolders matching 21st.dev structure.

Before:
  components/author__slug.json

After:
  components/marketing-blocks/hero/author__slug.json
  components/ui-components/button/author__slug.json
  ...
  components/index.json  (updated with new paths)
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent / "components"

# Map category_group → folder name
GROUP_FOLDERS = {
    "Marketing Blocks": "marketing-blocks",
    "UI Components": "ui-components",
}

# Map category slug → friendly folder name
CATEGORY_FOLDERS = {
    # Marketing Blocks
    "announcement": "announcements",
    "background": "backgrounds",
    "border": "borders",
    "call-to-action": "calls-to-action",
    "clients": "clients",
    "comparison": "comparisons",
    "dock": "docks",
    "features": "features",
    "footer": "footers",
    "hero": "heroes",
    "hook": "hooks",
    "image": "images",
    "map": "maps",
    "navbar-navigation": "navigation-menus",
    "pricing-section": "pricing-sections",
    "scroll-area": "scroll-areas",
    "shader": "shaders",
    "testimonials": "testimonials",
    "text": "texts",
    "video": "videos",
    # UI Components
    "accordion": "accordions",
    "ai-chat": "ai-chats",
    "alert": "alerts",
    "avatar": "avatars",
    "badge": "badges",
    "button": "buttons",
    "calendar": "calendars",
    "card": "cards",
    "carousel": "carousels",
    "checkbox": "checkboxes",
    "date-picker": "date-pickers",
    "modal-dialog": "dialogs-modals",
    "dropdown": "dropdowns",
    "empty-state": "empty-states",
    "file-tree": "file-trees",
    "upload-download": "file-uploads",
    "form": "forms",
    "icons": "icons",
    "input": "inputs",
    "link": "links",
    "menu": "menus",
    "notification": "notifications",
    "number": "numbers",
    "pagination": "paginations",
    "popover": "popovers",
    "radio-group": "radio-groups",
    "select": "selects",
    "sidebar": "sidebars",
    "sign-in": "sign-ins",
    "registration-signup": "sign-ups",
    "slider": "sliders",
    "spinner-loader": "spinner-loaders",
    "table": "tables",
    "tabs": "tabs",
    "chip-tag": "tags",
    "textarea": "text-areas",
    "toast": "toasts",
    "toggle": "toggles",
    "tooltip": "tooltips",
}


def main() -> None:
    moved = 0
    skipped = 0
    unknown = 0

    for json_file in sorted(ROOT.glob("*.json")):
        if json_file.name == "index.json":
            continue

        try:
            data = json.loads(json_file.read_text())
        except Exception:
            continue

        meta = data.get("_meta", {})
        # Fall back to _source for files from the original featured crawl
        if not meta and "_source" in data:
            src = data["_source"]
            meta = {"author": src.get("author", ""), "slug": src.get("name", ""), "registry_url": src.get("registry_url", "")}
        category = meta.get("category", "")
        group = meta.get("category_group", "")

        group_folder = GROUP_FOLDERS.get(group)
        cat_folder = CATEGORY_FOLDERS.get(category)

        if not group_folder or not cat_folder:
            print(f"  unknown category '{category}' / '{group}': {json_file.name}")
            unknown += 1
            continue

        dest_dir = ROOT / group_folder / cat_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / json_file.name

        if dest.exists():
            json_file.unlink()
            skipped += 1
        else:
            shutil.move(str(json_file), str(dest))
            moved += 1

    print(f"Moved: {moved}, Already there: {skipped}, Unknown category: {unknown}")

    # Rebuild index with updated file paths
    index = []
    for json_file in sorted(ROOT.rglob("*.json")):
        if json_file.name == "index.json":
            continue
        try:
            d = json.loads(json_file.read_text())
            meta = d.get("_meta", {})
            rel_path = json_file.relative_to(ROOT)
            index.append({
                "file": str(rel_path),
                "name": d.get("name", ""),
                "title": d.get("title", "") or meta.get("title", ""),
                "description": d.get("description", "") or meta.get("description", ""),
                "author": meta.get("author", ""),
                "category": meta.get("category", ""),
                "category_label": CATEGORY_FOLDERS.get(meta.get("category", ""), meta.get("category", "")),
                "category_group": meta.get("category_group", ""),
                "registry_url": meta.get("registry_url", ""),
                "dependencies": d.get("dependencies", []),
                "files": [fi.get("path", "") for fi in d.get("files", [])],
            })
        except Exception:
            pass

    index_file = ROOT / "index.json"
    index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"Index updated: {len(index)} components")


if __name__ == "__main__":
    main()
