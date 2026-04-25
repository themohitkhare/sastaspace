# Audio Designer — NLP to Audio System

## What it is

A web tool where you describe a project in plain language and get back generated audio files ready to use. Works for web/mobile apps, games, and videos.

## Output

Real `.wav` audio files — either a single piece or a full set:
- Background music
- UI sound loop
- Notification tone

All downloadable as a zip.

## Input style

Start high-level ("a meditation app for stressed professionals"), optionally go detailed. The tool handles both.

## Architecture

Fits into the existing sastaspace monorepo — no new infrastructure.

**Frontend:** New page at `apps/landing/src/app/lab/audio-designer/` — follows the existing lab page pattern (`TopNav`, `Footer`, `landing.module.css`).

**Backend:** New `services/audio-designer/` service — mirrors `services/auth/` structure (FastAPI + uvicorn, same `pyproject.toml`/`Dockerfile`/`src`/`tests` layout). Single endpoint: `POST /generate`.

**Pipeline:**
```
Lab page → POST /generate → Ollama (prompt expansion) → MusicGen ×3 → zip → download
```

**Ollama** — reused from existing infra, expands the project description into 3 MusicGen-ready prompts.

**MusicGen** (`facebook/musicgen-small` via `audiocraft`) — only new dependency, generates the audio.

## Key decisions

- Open-source / local only — no hosted API costs
- 3 fixed output tracks per generation (background, loop, notification) for MVP simplicity
- Follows `services/auth/` Python pattern exactly
- Runs on CPU by default, GPU if available
