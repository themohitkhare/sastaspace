"""Deck FastAPI app — describe a project, get a zip of WAVs.

Two routes:
  POST /plan      {description, count}  → JSON list of planned tracks
  POST /generate  {description, count}  → application/zip with one WAV per track

Health: GET /healthz

The split lets the frontend show step 2 (review/edit the plan) without paying
for full audio generation, then call /generate with the (possibly edited) plan
once the user is happy.
"""

from __future__ import annotations

import io
import logging
import os
import re
import sys
import zipfile
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .plan import PlannedTrack, draft_plan
from .render import RenderUnavailableError, render_wav

log = logging.getLogger("sastaspace.deck")


def env(name: str, default: str | None = None, *, required: bool = True) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        log.error("missing required env: %s", name)
        sys.exit(2)
    return val or ""


# ---------- config ----------
OLLAMA_URL = env("OLLAMA_URL", "", required=False)
OLLAMA_MODEL = env("OLLAMA_MODEL", "gemma3:1b", required=False)
PREFER_MUSICGEN = env("PREFER_MUSICGEN", "0", required=False) == "1"
ALLOWED_ORIGINS = [
    o.strip()
    for o in env(
        "ALLOWED_ORIGINS",
        "https://sastaspace.com,https://deck.sastaspace.com",
        required=False,
    ).split(",")
    if o.strip()
]


# ---------- request/response shapes ----------
class GenerateRequest(BaseModel):
    description: str = Field(..., min_length=4, max_length=600)
    count: int = Field(default=3, ge=1, le=10)
    # Optional pre-edited plan from the frontend's review step. When omitted,
    # the service drafts a fresh plan from `description`.
    tracks: list["TrackInput"] | None = None


class TrackInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    type: str = Field(default="loop", max_length=24)
    length: int = Field(default=15, ge=1, le=180)
    desc: str = Field(default="", max_length=240)
    tempo: str = Field(default="90bpm", max_length=24)
    instruments: str = Field(default="", max_length=240)
    mood: str = Field(default="focused", max_length=24)


GenerateRequest.model_rebuild()


class PlanResponse(BaseModel):
    tracks: list[dict]


# ---------- app + lifecycle ----------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("deck ready: ollama=%s prefer_musicgen=%s", OLLAMA_URL or "(local-fallback)", PREFER_MUSICGEN)
    yield


app = FastAPI(title="sastaspace-deck", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/plan", response_model=PlanResponse)
def plan_route(body: GenerateRequest) -> PlanResponse:
    """Draft a track plan from a project description."""
    plan = draft_plan(
        body.description.strip(),
        body.count,
        ollama_url=OLLAMA_URL or None,
        ollama_model=OLLAMA_MODEL,
    )
    return PlanResponse(tracks=[_track_to_dict(t) for t in plan])


@app.post("/generate")
def generate_route(body: GenerateRequest) -> Response:
    """Render a zip of WAVs.

    If ``tracks`` is provided (the user's edited plan), use that directly.
    Otherwise draft a plan from ``description`` first.
    """
    description = body.description.strip()
    if body.tracks:
        plan = [_input_to_planned(t) for t in body.tracks]
    else:
        plan = draft_plan(
            description,
            body.count,
            ollama_url=OLLAMA_URL or None,
            ollama_model=OLLAMA_MODEL,
        )

    if not plan:
        raise HTTPException(status_code=400, detail="no tracks to generate")

    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "README.txt",
                _readme(description, plan),
            )
            used_names: set[str] = set()
            for i, track in enumerate(plan, start=1):
                wav_bytes = render_wav(track, prefer_musicgen=PREFER_MUSICGEN)
                filename = _unique_filename(track.name, i, used_names)
                zf.writestr(filename, wav_bytes)
    except RenderUnavailableError as exc:
        # No real renderer wired up — refuse instead of returning the old
        # placeholder sine waves. The STDB worker is the production path.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="deck.zip"'},
    )


# ---------- internals ----------
def _track_to_dict(t: PlannedTrack) -> dict:
    d = asdict(t)
    d["musicgen_prompt"] = t.musicgen_prompt
    return d


def _input_to_planned(t: TrackInput) -> PlannedTrack:
    return PlannedTrack(
        name=t.name,
        type=t.type,
        length=t.length,
        desc=t.desc,
        tempo=t.tempo,
        instruments=t.instruments,
        mood=t.mood,
    )


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(s: str) -> str:
    cleaned = _SLUG_RE.sub("-", s.lower()).strip("-")[:30]
    return cleaned or "track"


def _unique_filename(name: str, idx: int, used: set[str]) -> str:
    base = _slugify(name)
    candidate = f"{idx:02d}-{base}.wav"
    if candidate in used:
        candidate = f"{idx:02d}-{base}-{idx}.wav"
    used.add(candidate)
    return candidate


def _readme(description: str, plan: list[PlannedTrack]) -> str:
    lines = [
        "deck — sastaspace audio designer",
        "================================",
        "",
        f"brief: {description}",
        "",
        "tracks:",
    ]
    for i, t in enumerate(plan, start=1):
        lines.append(f"  {i:02d}. {t.name} — {t.type} · {t.mood} · {t.length}s")
        lines.append(f"      {t.musicgen_prompt}")
    lines.append("")
    lines.append("license: cc-by 4.0")
    return "\n".join(lines)


@app.exception_handler(404)
async def not_found(_request, _exc):
    return JSONResponse(status_code=404, content={"detail": "not found"})


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8081")))  # noqa: S104


if __name__ == "__main__":
    main()
