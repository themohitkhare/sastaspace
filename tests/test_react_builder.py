# tests/test_react_builder.py
"""Tests for sastaspace.react_builder — import sanitisation and file parsing."""

from __future__ import annotations

from sastaspace.react_builder import (
    _sanitize_imports,
    _strip_broken_relative_imports,
    parse_composer_output,
)

# --- parse_composer_output ---


class TestParseComposerOutput:
    def test_basic_file_delimiters(self):
        raw = (
            "--- FILE: src/App.tsx ---\n"
            "export default function App() { return <div /> }\n"
            "--- FILE: src/globals.css ---\n"
            "body { margin: 0; }\n"
        )
        result = parse_composer_output(raw)
        assert "src/App.tsx" in result
        assert "src/globals.css" in result
        assert "export default" in result["src/App.tsx"]

    def test_strips_markdown_code_fences(self):
        raw = (
            "--- FILE: src/App.tsx ---\n"
            "```tsx\n"
            "export default function App() { return <div /> }\n"
            "```\n"
        )
        result = parse_composer_output(raw)
        assert "```" not in result["src/App.tsx"]

    def test_empty_input_returns_empty(self):
        assert parse_composer_output("") == {}

    def test_fallback_single_component(self):
        raw = "import React from 'react'\nexport default function App() {}"
        result = parse_composer_output(raw)
        assert "src/App.tsx" in result

    def test_no_fallback_for_plain_text(self):
        assert parse_composer_output("hello world") == {}


# --- _sanitize_imports ---


class TestSanitizeImports:
    def test_allows_react_imports(self):
        files = {"src/App.tsx": 'import React from "react";\n'}
        result = _sanitize_imports(files)
        assert 'import React from "react"' in result["src/App.tsx"]

    def test_strips_unknown_package(self):
        files = {"src/App.tsx": 'import X from "@tabler/icons-react";\n'}
        result = _sanitize_imports(files)
        assert "STRIPPED" in result["src/App.tsx"]

    def test_allows_radix_ui(self):
        files = {"src/App.tsx": 'import { Dialog } from "@radix-ui/react-dialog";\n'}
        result = _sanitize_imports(files)
        assert "STRIPPED" not in result["src/App.tsx"]

    def test_allows_relative_imports(self):
        files = {"src/App.tsx": 'import { Button } from "./components/button";\n'}
        result = _sanitize_imports(files)
        assert "STRIPPED" not in result["src/App.tsx"]

    def test_allows_alias_imports(self):
        files = {"src/App.tsx": 'import { cn } from "@/lib/utils";\n'}
        result = _sanitize_imports(files)
        assert "STRIPPED" not in result["src/App.tsx"]

    def test_skips_non_ts_files(self):
        files = {"src/globals.css": '@import "tailwindcss/base";'}
        result = _sanitize_imports(files)
        assert result["src/globals.css"] == files["src/globals.css"]


# --- _strip_broken_relative_imports ---


class TestStripBrokenRelativeImports:
    def test_keeps_valid_relative_import(self):
        files = {
            "src/components/ui/button.tsx": "export function Button() {}",
            "src/App.tsx": 'import { Button } from "./components/ui/button";\n',
        }
        result = _strip_broken_relative_imports(files)
        assert "STRIPPED" not in result["src/App.tsx"]

    def test_strips_missing_relative_import(self):
        files = {
            "src/components/ui/commerce-hero.tsx": (
                'import { Sheet } from "../sheet";\nexport function CommerceHero() {}'
            ),
        }
        result = _strip_broken_relative_imports(files)
        assert "STRIPPED: missing file" in result["src/components/ui/commerce-hero.tsx"]

    def test_keeps_parent_dir_import_when_file_exists(self):
        files = {
            "src/components/ui/sheet.tsx": "export function Sheet() {}",
            "src/components/ui/hero.tsx": 'import { Sheet } from "./sheet";\n',
        }
        result = _strip_broken_relative_imports(files)
        assert "STRIPPED" not in result["src/components/ui/hero.tsx"]

    def test_strips_deep_relative_that_doesnt_exist(self):
        files = {
            "src/App.tsx": 'import { Foo } from "./lib/nonexistent";\nexport default () => null;',
        }
        result = _strip_broken_relative_imports(files)
        assert "STRIPPED: missing file" in result["src/App.tsx"]

    def test_skips_non_code_files(self):
        files = {
            "src/globals.css": '@import "./reset.css";',
        }
        result = _strip_broken_relative_imports(files)
        assert result["src/globals.css"] == files["src/globals.css"]

    def test_multiple_imports_mixed(self):
        files = {
            "src/components/ui/utils.ts": "export const cn = () => '';",
            "src/App.tsx": (
                'import { cn } from "./components/ui/utils";\n'
                'import { Missing } from "./components/ui/missing";\n'
                "export default () => null;"
            ),
        }
        result = _strip_broken_relative_imports(files)
        content = result["src/App.tsx"]
        assert "import { cn }" in content
        assert "STRIPPED: missing file" in content
        assert "missing" in content.lower()
