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
