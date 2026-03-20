# SastaSpace — AI Website Redesigner

Enter any website URL → get a beautiful AI-redesigned version in your browser in under 60 seconds.

## Quick Start

```bash
# 1. Install dependencies
uv sync
uv run playwright install chromium

# 2. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Redesign a website
sastaspace redesign https://example.com
```

## Commands

| Command | Description |
|---------|-------------|
| `sastaspace redesign <url>` | Full pipeline: crawl → AI redesign → preview |
| `sastaspace redesign <url> -s myname` | Use custom subdomain |
| `sastaspace redesign <url> --no-open` | Skip auto-opening browser |
| `sastaspace list` | List all redesigned sites |
| `sastaspace open <subdomain>` | Open a site in browser |
| `sastaspace remove <subdomain>` | Remove a site |
| `sastaspace serve` | Start preview server (foreground) |

## How It Works

1. **Crawl** — Playwright headless browser renders the target site, extracts content + screenshot
2. **Redesign** — Claude AI analyzes screenshot + content, generates a modern single-file HTML redesign
3. **Deploy** — HTML saved to `sites/{subdomain}/index.html`
4. **Serve** — FastAPI server at `http://localhost:8080` serves all redesigns

## Configuration (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...  # Required
SITES_DIR=./sites             # Where to save redesigns (default: ./sites)
SERVER_PORT=8080              # Preview server port (default: 8080)
CLAUDE_MODEL=claude-sonnet-4-20250514  # Claude model (default)
```
