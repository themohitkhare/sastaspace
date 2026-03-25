# sastaspace/react_builder.py
"""Vite-based React builder for the component-based redesign pipeline.

Takes generated React source files (from the Composer LLM), writes them into
a template Vite project, runs `vite build`, and returns the built output.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache the template mtime so we can skip re-checking node_modules on repeat builds
_template_deps_verified: dict[str, bool] = {}


class BuildError(Exception):
    """Raised when the Vite build fails."""


def is_node_available() -> bool:
    """Check if Node.js is available on the system."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ensure_template_deps(template_dir: Path) -> None:
    """Install template dependencies if node_modules doesn't exist.

    Caches the check per template_dir path to avoid repeated filesystem lookups
    across multiple builds in the same process.
    """
    key = str(template_dir)
    if key in _template_deps_verified:
        return

    nm_path = template_dir / "node_modules"
    if nm_path.exists():
        _template_deps_verified[key] = True
        return

    logger.info("Installing template dependencies in %s", template_dir)
    result = subprocess.run(
        ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"],
        cwd=template_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise BuildError(f"npm install failed: {result.stderr[:500]}")
    _template_deps_verified[key] = True
    logger.info("Template dependencies installed")


def parse_composer_output(raw: str) -> dict[str, str]:
    """Parse the Composer LLM output into a map of file paths to content.

    The Composer outputs files delimited by:
        --- FILE: src/App.tsx ---
        content here
        --- FILE: src/globals.css ---
        content here

    Returns:
        Dict mapping relative file paths to their content.
    """
    files: dict[str, str] = {}

    # Split on file delimiters
    pattern = r"---\s*FILE:\s*(.+?)\s*---"
    parts = re.split(pattern, raw)

    # parts[0] is anything before the first delimiter (usually empty)
    # Then alternating: path, content, path, content, ...
    i = 1
    while i < len(parts) - 1:
        path = parts[i].strip()
        content = parts[i + 1].strip()

        # Strip markdown code fences if the LLM wrapped them
        content = re.sub(r"^```(?:tsx|ts|css|json)?\s*\n?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\n?```\s*$", "", content, flags=re.IGNORECASE)
        # Strip trailing bare `---` delimiters the LLM sometimes adds as closing markers
        content = re.sub(r"\n---\s*$", "", content)
        content = content.strip()

        if path and content:
            files[path] = content

        i += 2

    if not files:
        # Fallback: try to find a single React component in the output
        logger.warning("No file delimiters found in composer output, attempting fallback parse")
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:tsx|ts)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned, flags=re.IGNORECASE)
        if cleaned and ("import" in cleaned or "export" in cleaned):
            files["src/App.tsx"] = cleaned

    return files


def _copy_template(template_dir: Path, dest: Path) -> None:
    """Copy template files (excluding node_modules and dotfiles) into dest."""
    for item in template_dir.iterdir():
        if item.name == "node_modules" or item.name.startswith("."):
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)

    # Symlink node_modules from template (fast, avoids re-install)
    nm_src = template_dir / "node_modules"
    if nm_src.exists():
        os.symlink(nm_src.resolve(), dest / "node_modules")
    else:
        raise BuildError("Template node_modules not found — run npm install first")


# Packages available in redesign-template/package.json — imports outside this set
# are stripped by _sanitize_imports to prevent Vite build failures.
_ALLOWED_PACKAGES = {
    "react",
    "react-dom",
    "react-icons",
    "lucide-react",
    "framer-motion",
    "motion",
    "clsx",
    "class-variance-authority",
    "tailwind-merge",
    "embla-carousel-react",
}
# @radix-ui/* and @/ (alias) are also allowed — matched by prefix
_ALLOWED_PREFIXES = ("@radix-ui/", "@/", "./", "../", "react-icons/")


def _is_allowed_import(module: str) -> bool:
    """Check if a module import is available in the build template."""
    if module in _ALLOWED_PACKAGES:
        return True
    return any(module.startswith(p) for p in _ALLOWED_PREFIXES)


def _sanitize_imports(files: dict[str, str]) -> dict[str, str]:
    """Remove import statements for unavailable packages from generated files.

    This prevents Vite build failures from LLM-hallucinated package imports.
    Lines importing unknown packages are commented out with a warning.
    Also validates lucide-react icon names, replacing non-existent icons with Circle.
    """
    import_pattern = re.compile(
        r'^(import\s+.*\s+from\s+["\'])([^"\']+)(["\'];?\s*)$', re.MULTILINE
    )
    lucide_icons = _load_lucide_icon_names()

    # Pattern to match: import { Icon1, Icon2 } from 'lucide-react'
    lucide_import_re = re.compile(
        r"""^(import\s*\{)([^}]+)(\}\s*from\s*['"]lucide-react['"];?\s*)$""",
        re.MULTILINE,
    )

    sanitized = {}
    for path, content in files.items():
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            sanitized[path] = content
            continue

        def _check_import(m: re.Match) -> str:
            module = m.group(2)
            if _is_allowed_import(module):
                return m.group(0)
            logger.warning("Stripped unavailable import: %s (from %s)", module, path)
            return f"// STRIPPED: unavailable package — {m.group(0)}"

        content = import_pattern.sub(_check_import, content)

        # Validate lucide-react icon names if we have the icon set loaded
        if lucide_icons:

            def _fix_lucide_icons(m: re.Match) -> str:
                prefix = m.group(1)
                names_str = m.group(2)
                suffix = m.group(3)

                names = [n.strip() for n in names_str.split(",") if n.strip()]
                fixed_names: list[str] = []
                for name in names:
                    # Handle "Icon as Alias" syntax
                    parts = name.split(" as ")
                    icon_name = parts[0].strip()
                    if icon_name not in lucide_icons:
                        logger.warning(
                            "Replaced non-existent lucide icon '%s' with 'Circle' in %s",
                            icon_name,
                            path,
                        )
                        if len(parts) > 1:
                            fixed_names.append(f"Circle as {parts[1].strip()}")
                        else:
                            fixed_names.append(f"Circle as {icon_name}")
                    else:
                        fixed_names.append(name)

                return f"{prefix} {', '.join(fixed_names)} {suffix}"

            content = lucide_import_re.sub(_fix_lucide_icons, content)

        sanitized[path] = content

    return sanitized


@lru_cache(maxsize=1)
def _load_lucide_icon_names() -> frozenset[str]:
    """Load valid lucide-react icon export names from the template's node_modules.

    Parses the ESM icons index.js to extract all ``export { default as IconName }``
    entries.  Returns a frozenset for O(1) lookups.  Cached so the file is read at
    most once per process.
    """
    candidates = [
        Path("redesign-template/node_modules/lucide-react/dist/esm/icons/index.js"),
        Path("redesign-template/node_modules/lucide-react/dist/cjs/lucide-react.js"),
    ]
    for rel in candidates:
        p = Path(__file__).resolve().parent.parent / rel
        if p.exists():
            text = p.read_text(encoding="utf-8")
            names = set(re.findall(r"export\s*\{\s*default\s+as\s+(\w+)\s*\}", text))
            if names:
                logger.info("Loaded %d lucide-react icon names from %s", len(names), p)
                return frozenset(names)

    logger.warning("Could not locate lucide-react icon index — icon validation disabled")
    return frozenset()


def _fix_css_import_ordering(files: dict[str, str]) -> dict[str, str]:
    """Move all CSS @import statements to the top of each .css file.

    CSS spec requires @import rules to precede all other rules (except @charset
    and @layer).  LLMs frequently place @import after @tailwind or :root blocks,
    causing build failures in ~15-20%% of generations.
    """
    fixed: dict[str, str] = {}
    import_re = re.compile(r"^\s*@import\s", re.IGNORECASE)

    for path, content in files.items():
        if not path.endswith(".css"):
            fixed[path] = content
            continue

        lines = content.splitlines(keepends=True)
        import_lines: list[str] = []
        other_lines: list[str] = []

        for line in lines:
            if import_re.match(line):
                import_lines.append(line)
            else:
                other_lines.append(line)

        if import_lines:
            logger.info(
                "Reordered %d @import statement(s) to top of %s",
                len(import_lines),
                path,
            )
            fixed[path] = "".join(import_lines) + "".join(other_lines)
        else:
            fixed[path] = content

    return fixed


def _esbuild_validate(files: dict[str, str], template_dir: Path) -> None:
    """Run esbuild syntax validation on each .tsx/.ts file.

    Takes ~7ms per file.  Raises BuildError with the file path and error details
    on syntax errors.  Gracefully skips if esbuild binary is not found.
    """
    esbuild_bin = template_dir / "node_modules" / ".bin" / "esbuild"
    if not esbuild_bin.exists():
        # Try system-level esbuild
        esbuild_bin_str = shutil.which("esbuild")
        if not esbuild_bin_str:
            logger.debug("esbuild not found — skipping pre-validation")
            return
        esbuild_bin = Path(esbuild_bin_str)

    for path, content in files.items():
        if not path.endswith((".tsx", ".ts")):
            continue

        ext = path.rsplit(".", 1)[-1]
        try:
            result = subprocess.run(
                [str(esbuild_bin), f"--loader={ext}"],
                input=content,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.debug("esbuild validation skipped for %s: %s", path, exc)
            continue

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500]
            raise BuildError(f"Syntax error in {path}:\n{stderr}")


def _write_generated_files(files: dict[str, str], project_dir: Path) -> None:
    """Write generated source files into the project directory."""
    for rel_path, content in files.items():
        file_path = project_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _run_vite_build(project_dir: Path) -> Path:
    """Run ``npx vite build`` and return the dist directory path.

    Raises BuildError on failure or missing output.
    """
    logger.info("Running Vite build in %s", project_dir)
    env = {**os.environ, "NODE_ENV": "production"}
    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    if result.returncode != 0:
        stderr = result.stderr[:1000] if result.stderr else ""
        stdout = result.stdout[:500] if result.stdout else ""
        logger.error("Vite build failed:\nstderr: %s\nstdout: %s", stderr, stdout)
        raise BuildError(f"Vite build failed: {stderr}")

    dist_path = project_dir / "dist"
    if not dist_path.exists() or not (dist_path / "index.html").exists():
        raise BuildError("Vite build produced no output — dist/index.html missing")

    return dist_path


def build_react_page(
    files: dict[str, str],
    template_dir: Path,
    output_dir: Path,
    brand_css_vars: dict[str, str] | None = None,
) -> Path:
    """Build a React page using Vite.

    Args:
        files: Map of relative file paths to content (from Composer output).
        template_dir: Path to redesign-template/ with pre-installed deps.
        output_dir: Where to put the built output.
        brand_css_vars: Optional CSS custom property overrides for branding.

    Returns:
        Path to the built output directory.

    Raises:
        BuildError: If the build fails.
    """
    import time as _time

    if not is_node_available():
        raise BuildError("Node.js not available — cannot build React pages")

    _ensure_template_deps(template_dir)

    with tempfile.TemporaryDirectory(prefix="sastaspace-build-") as tmp:
        tmp_path = Path(tmp)

        t_copy = _time.monotonic()
        _copy_template(template_dir, tmp_path)
        files = _sanitize_imports(files)
        files = _fix_css_import_ordering(files)
        _esbuild_validate(files, template_dir)
        _write_generated_files(files, tmp_path)
        logger.info(
            "PERF | react_build template_copy=%.2fs files=%d",
            _time.monotonic() - t_copy,
            len(files),
        )

        if brand_css_vars:
            _inject_css_vars(tmp_path, brand_css_vars)

        t_vite = _time.monotonic()
        dist_path = _run_vite_build(tmp_path)
        logger.info("PERF | react_build vite_build=%.1fs", _time.monotonic() - t_vite)

        # Inline all CSS/JS assets into index.html so the result is a single
        # self-contained file. This avoids CORS issues when the HTML is served
        # from api.sastaspace.com but embedded in an iframe on sastaspace.com.
        _inline_assets(dist_path)

        # Copy dist to output
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(dist_path, output_dir)

        build_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
        file_count = sum(1 for _ in output_dir.rglob("*") if _.is_file())
        logger.info(
            "Vite build complete: %d files, %.1f KB total",
            file_count,
            build_size / 1024,
        )

        return output_dir


def _inline_assets(dist_path: Path) -> None:
    """Inline all CSS and JS assets into index.html.

    Replaces <link rel="stylesheet" href="/assets/..."> with <style>...</style>
    and <script type="module" src="/assets/..."> with <script>...</script>.
    Removes the separate asset files afterward.
    """
    index_html = dist_path / "index.html"
    if not index_html.exists():
        return

    html = index_html.read_text(encoding="utf-8")
    assets_dir = dist_path / "assets"
    if not assets_dir.exists():
        return

    # Inline CSS: <link rel="stylesheet" ... href="/assets/xxx.css">
    for css_file in sorted(assets_dir.glob("*.css")):
        css_content = css_file.read_text(encoding="utf-8")
        pattern = rf'<link[^>]*href="[./]*assets/{re.escape(css_file.name)}"[^>]*/?\s*>'
        # Use lambda to avoid re.sub interpreting \u escapes in CSS as backreferences
        html = re.sub(pattern, lambda _: f"<style>{css_content}</style>", html)

    # Inline JS: <script type="module" ... src="/assets/xxx.js">
    for js_file in sorted(assets_dir.glob("*.js")):
        js_content = js_file.read_text(encoding="utf-8")
        pattern = (
            rf'<script[^>]*src="[./]*assets/{re.escape(js_file.name)}"[^>]*>'
            r"</script>"
        )
        # Use lambda to avoid re.sub interpreting \u escapes in JS as backreferences
        html = re.sub(pattern, lambda _: f'<script type="module">{js_content}</script>', html)

    index_html.write_text(html, encoding="utf-8")

    # Remove assets directory — everything is inlined
    shutil.rmtree(assets_dir, ignore_errors=True)

    logger.info("Assets inlined into index.html — single-file output")


def _inject_css_vars(project_dir: Path, css_vars: dict[str, str]) -> None:
    """Inject CSS custom properties into the globals.css file."""
    globals_css = project_dir / "src" / "globals.css"
    if not globals_css.exists():
        return

    # Build CSS variable declarations
    var_lines = [f"    {name}: {value};" for name, value in css_vars.items()]
    var_block = "\n".join(var_lines)

    content = globals_css.read_text()

    # Insert after :root {
    if ":root {" in content:
        content = content.replace(
            ":root {",
            f":root {{\n{var_block}",
            1,
        )
        # Fix the double brace
        content = content.replace(":root {{\n", ":root {\n", 1)
    else:
        content = f":root {{\n{var_block}\n}}\n\n{content}"

    globals_css.write_text(content, encoding="utf-8")
