"""Admin API for sastaspace.

Routes:
  GET  /system              — psutil metrics, polled every 3s
  GET  /containers          — docker container status, polled every 15s
  GET  /logs/{container}    — SSE docker log stream
  POST /stdb/comments/{id}/status  — write proxy (Google JWT auth)
  DELETE /stdb/comments/{id}       — write proxy (Google JWT auth)
  GET  /healthz
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

import google.auth.transport.requests
import google.oauth2.id_token
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .docker_client import known_container_names, list_containers, stream_logs
from .stdb import SpacetimeClient
from .system import get_metrics

log = logging.getLogger("sastaspace.admin-api")


def env(name: str, default: str | None = None, *, required: bool = True) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        log.error("missing required env: %s", name)
        sys.exit(2)
    return val or ""


STDB_URL = env("STDB_HTTP_URL", "http://127.0.0.1:3100", required=False)
STDB_MODULE = env("STDB_MODULE", "sastaspace", required=False)
SPACETIME_TOKEN = env("SPACETIME_TOKEN")
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
OWNER_EMAIL = env("OWNER_EMAIL")
ALLOWED_ORIGINS = [o.strip() for o in env("ALLOWED_ORIGINS", "https://admin.sastaspace.com", required=False).split(",") if o.strip()]

_GOOGLE_REQUEST = google.auth.transport.requests.Request()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stdb = SpacetimeClient(STDB_URL, STDB_MODULE, SPACETIME_TOKEN)
    log.info("admin-api ready: stdb=%s owner=%s", STDB_URL, OWNER_EMAIL)
    yield
    stdb = getattr(app.state, "stdb", None)
    if stdb is not None:
        stdb.close()


app = FastAPI(title="sastaspace-admin-api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------- auth dependency ----------

def require_owner(authorization: str = Header(...)) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        id_info = google.oauth2.id_token.verify_oauth2_token(token, _GOOGLE_REQUEST, GOOGLE_CLIENT_ID)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc
    if id_info.get("email") != OWNER_EMAIL:
        raise HTTPException(status_code=403, detail="not the owner")


# ---------- routes ----------

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/system")
def system_metrics() -> dict:
    return get_metrics()


@app.get("/containers")
def containers() -> list:
    try:
        return list_containers()
    except Exception as exc:  # noqa: BLE001
        log.exception("containers list failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


_TAIL_DEFAULT = 200
_TAIL_MAX = 1000


@app.get("/logs/{container_name}")
async def logs(
    container_name: str,
    tail: int = Query(default=_TAIL_DEFAULT, ge=1, le=_TAIL_MAX),
) -> StreamingResponse:
    allowed = known_container_names()
    if container_name not in allowed:
        raise HTTPException(status_code=404, detail=f"unknown container: {container_name!r}")

    return StreamingResponse(
        stream_logs(container_name, tail=tail),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


class StatusBody(BaseModel):
    status: str

    def validate_status(self) -> str:
        if self.status not in ("approved", "flagged", "rejected"):
            raise HTTPException(status_code=422, detail="status must be approved | flagged | rejected")
        return self.status


@app.post("/stdb/comments/{comment_id}/status", dependencies=[Depends(require_owner)])
def set_comment_status(comment_id: int, body: StatusBody) -> dict:
    body.validate_status()
    try:
        app.state.stdb.set_comment_status(comment_id, body.status)
    except Exception as exc:  # noqa: BLE001
        log.exception("set_comment_status failed for id=%s", comment_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True}


@app.delete("/stdb/comments/{comment_id}", dependencies=[Depends(require_owner)])
def delete_comment(comment_id: int) -> dict:
    try:
        app.state.stdb.delete_comment(comment_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("delete_comment failed for id=%s", comment_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True}


@app.exception_handler(404)
async def not_found(_request, _exc):
    return JSONResponse(status_code=404, content={"detail": "not found"})


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "3170")))  # noqa: S104


if __name__ == "__main__":
    main()
