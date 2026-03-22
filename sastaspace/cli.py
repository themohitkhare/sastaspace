# sastaspace/cli.py
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sastaspace.config import Settings
from sastaspace.crawler import crawl
from sastaspace.deployer import deploy, load_registry, save_registry
from sastaspace.redesigner import RedesignError, redesign
from sastaspace.server import ensure_running

console = Console()

DEFAULT_SITES_DIR = Path("./sites")


@click.group()
def main() -> None:
    """SastaSpace — AI Website Redesigner"""


def _crawl_site(url: str, progress: Progress, task) -> object:
    """Run the crawler and return result, handling errors with Rich panels."""
    try:
        crawl_result = asyncio.run(crawl(url))
    except (OSError, ConnectionError, TimeoutError) as e:
        progress.stop()
        console.print(Panel(f"[red]Crawl failed:[/red] {e}", title="Error"))
        raise SystemExit(1)

    if crawl_result.error:
        progress.stop()
        console.print(
            Panel(
                f"[red]Could not crawl {url}[/red]\n\n{crawl_result.error}\n\n"
                "Is the site accessible?",
                title="Crawl Error",
            )
        )
        raise SystemExit(1)

    progress.update(task, description=f"Crawled [bold]{crawl_result.title or url}[/bold] ✓")
    return crawl_result


def _redesign_site(crawl_result, cfg, progress: Progress, task) -> str:
    """Run the redesigner and return HTML, handling errors with Rich panels."""
    progress.update(task, description="Redesigning with Claude AI (this takes ~30s)...")
    try:
        return redesign(crawl_result, api_url=cfg.claude_code_api_url, model=cfg.claude_model)
    except RedesignError as e:
        progress.stop()
        console.print(Panel(f"[red]Redesign failed:[/red] {e}", title="Error"))
        raise SystemExit(1)
    except (ConnectionError, TimeoutError, OSError) as e:
        progress.stop()
        console.print(
            Panel(
                f"[red]Claude API error:[/red] {e}\n\nCheck your ANTHROPIC_API_KEY in .env",
                title="API Error",
            )
        )
        raise SystemExit(1)


@main.command("redesign")
@click.argument("url")
@click.option("-s", "--subdomain", default=None, help="Custom subdomain slug")
@click.option("--no-open", is_flag=True, default=False, help="Skip opening browser")
@click.option("--sites-dir", type=click.Path(), default=None)
def redesign_cmd(url: str, subdomain: str | None, no_open: bool, sites_dir: str | None) -> None:
    """Crawl, redesign, and deploy a website. Opens a local preview."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    cfg = _load_config()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Crawling website...", total=None)
        crawl_result = _crawl_site(url, progress, task)

        html = _redesign_site(crawl_result, cfg, progress, task)
        progress.update(task, description="Redesign complete ✓")

        progress.update(task, description="Deploying to local preview...")
        result = deploy(url=url, html=html, sites_dir=sites, subdomain=subdomain)
        progress.update(task, description=f"Deployed → {result.subdomain} ✓")

        progress.update(task, description="Starting preview server...")
        port = ensure_running(sites_dir=sites, preferred_port=cfg.server_port)
        preview_url = f"http://localhost:{port}/{result.subdomain}/"
        progress.update(task, description="Server ready ✓")

    console.print()
    console.print(
        Panel(
            f"[bold green]Redesign complete![/bold green]\n\n"
            f"Preview: [link={preview_url}]{preview_url}[/link]\n"
            f"Original: {url}",
            title="SastaSpace",
        )
    )

    if not no_open:
        webbrowser.open(preview_url)


@main.command("list")
@click.option("--sites-dir", type=click.Path(), default=None)
def list_cmd(sites_dir: str | None) -> None:
    """List all deployed redesigns."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    registry = load_registry(sites)

    if not registry:
        console.print("[dim]No sites redesigned yet. Run:[/dim] sastaspace redesign <url>")
        return

    table = Table(title="Deployed Redesigns", show_header=True)
    table.add_column("Subdomain", style="bold cyan")
    table.add_column("Original URL")
    table.add_column("Created")
    table.add_column("Status")

    for entry in sorted(registry, key=lambda e: e.get("timestamp", ""), reverse=True):
        table.add_row(
            entry["subdomain"],
            entry.get("original_url", ""),
            entry.get("timestamp", "")[:19].replace("T", " "),
            entry.get("status", ""),
        )

    console.print(table)


@main.command("open")
@click.argument("subdomain")
@click.option("--sites-dir", type=click.Path(), default=None)
def open_cmd(subdomain: str, sites_dir: str | None) -> None:
    """Open a deployed site in the browser."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    cfg = _load_config()
    port = ensure_running(sites_dir=sites, preferred_port=cfg.server_port)
    url = f"http://localhost:{port}/{subdomain}/"
    console.print(f"Opening [link={url}]{url}[/link]")
    webbrowser.open(url)


@main.command("remove")
@click.argument("subdomain")
@click.option("--sites-dir", type=click.Path(), default=None)
def remove_cmd(subdomain: str, sites_dir: str | None) -> None:
    """Remove a deployed site."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    site_path = sites / subdomain

    if not site_path.exists():
        console.print(f"[red]Not found:[/red] {subdomain}")
        raise SystemExit(1)

    click.confirm(f"Remove {subdomain}?", abort=True)

    shutil.rmtree(site_path)

    registry = load_registry(sites)
    registry = [e for e in registry if e.get("subdomain") != subdomain]
    save_registry(sites, registry)

    console.print(f"[green]Removed:[/green] {subdomain}")


@main.command("serve")
@click.option("--sites-dir", type=click.Path(), default=None)
def serve_cmd(sites_dir: str | None) -> None:
    """Start the preview server in the foreground (streams logs)."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    sites.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()

    env = {**os.environ, "SASTASPACE_SITES_DIR": str(sites.resolve())}

    console.print(f"Starting preview server at [bold]http://localhost:{cfg.server_port}[/bold]")
    console.print("Press Ctrl+C to stop.\n")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sastaspace.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(cfg.server_port),
            "--reload",
        ],
        env=env,
    )


def _load_config():
    return Settings()
