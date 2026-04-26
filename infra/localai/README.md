# LocalAI

Self-hosted, OpenAI-compatible model server. Sibling to Ollama. Runs as a
docker-compose service (`localai`) and exposes the OpenAI HTTP API on
`127.0.0.1:8080`.

## Dev vs prod images

| Environment | Image | Hardware | GPU mounts in compose |
|---|---|---|---|
| **Dev** (this repo's docker-compose, on a Mac dev machine) | `localai/localai:latest` (CPU) | CPU only | none |
| **Prod** (taxila — AMD 7900 XTX) | `localai/localai:latest-aio-gpu-hipblas` | ROCm GPU | `devices: [/dev/kfd, /dev/dri]` |

Dev uses the CPU image because the GPU passthrough mounts are AMD-Linux-specific
and would fail on Mac. Prod swaps to the HIPBLAS image and adds the device
mounts. Inference is dramatically slower on CPU (~30 s for a 4-second MusicGen
clip vs sub-second on GPU) but the API surface is identical, so wiring built
against dev works unchanged on prod.

## Files

- `models.yaml` — declares which models LocalAI should know about (mirrored into
  `models/models.yaml` because Docker can't bind-mount a single file inside an
  already-bind-mounted directory; see compose comment).
- `models/` — model weights live here (gitignored if it grows). LocalAI reads
  `models/models.yaml` at boot to pre-register entries.
- `preload.sh` — POSTs to `/models/apply` to fetch model weights on first boot.

## Phase 0 verification (2026-04-26)

The container brought up successfully on the dev machine and serves the OpenAI
API. `curl http://127.0.0.1:8080/v1/models` returns `musicgen-small` from the
preloaded `models.yaml` registry.

### Endpoint shape — IMPORTANT for Phase 1 W3

LocalAI v4.1.3 (the version pulled by `localai/localai:latest` on 2026-04-26)
**does not** expose `/v1/audio/generations` for music generation. The correct
path is:

```
POST /v1/sound-generation
Content-Type: application/json

{"model":"musicgen-small","input":"<prompt>","duration":4}
```

`/v1/audio/generations` returns `404`. `/v1/audio/transcriptions` exists but is
the speech-to-text path. Use `/v1/sound-generation` for MusicGen.

### Backend availability caveat

In v4.1.3 the `musicgen` backend is NOT bundled into the default `localai/localai:latest`
image. `/models/apply` accepts the request but the underlying download fails
because the backend manifest isn't in the bundled gallery (the gallery now
predominantly ships TTS and LLM backends — `qwen3-tts-cpp`, `parler-tts-mini-v0.1`,
`fish-speech-s2-pro`, etc., but no `musicgen`). The `/v1/sound-generation`
endpoint returns `400` with no model loaded.

**For Phase 1 W3 to actually generate audio, one of these must change:**
1. Switch to a LocalAI image variant that bundles musicgen (the AIO-CPU /
   AIO-GPU images bundle more backends — verify on prod with
   `docker exec sastaspace-localai ls /build/backend/python/`).
2. Manually install the musicgen backend into the `models/` dir per LocalAI's
   custom-backend docs.
3. Use a different audio model that IS in the v4.1.3 default gallery
   (`parler-tts-mini-v0.1` is a TTS model — would change the deck-agent UX).

Phase 0's goal is to prove the deployment path; Phase 1 W3 picks a concrete
musicgen install strategy.

### Phase 1 W3 status (2026-04-26) — deferred to prod

The W3 worker is **wired against the verified `/v1/sound-generation` endpoint
shape** documented above. Local end-to-end smoke against the real LocalAI
endpoint is **deferred to taxila** for the following reasons:

1. The AIO-CPU image (`localai/localai:latest-aio-cpu`) is ~50 GB+ and the dev
   Mac currently has ~25 GB free — pulling it would fill the disk.
2. The dev Mac is ARM64 (Apple Silicon); the AIO-CPU image targets x86_64
   primarily and would run under emulation, making MusicGen unusably slow.
3. The intended prod target is `localai/localai:latest-aio-gpu-hipblas` on
   taxila's AMD 7900 XTX — the AIO image variant where MusicGen actually fits
   the deployment story.

**Action when this lands on taxila:**

```bash
# On taxila, swap the compose image:
sed -i 's|localai/localai:latest|localai/localai:latest-aio-gpu-hipblas|' \
    infra/docker-compose.yml
# Add the AMD GPU device mounts under the localai service:
#   devices:
#     - /dev/kfd
#     - /dev/dri
docker compose pull localai
docker compose up -d localai
# Verify the musicgen backend is bundled:
docker exec sastaspace-localai ls /build/backend/python/ | grep musicgen
# Smoke test:
curl -fsSL -X POST http://127.0.0.1:8080/v1/sound-generation \
  -H 'Content-Type: application/json' \
  -d '{"model":"musicgen-small","input":"calm ambient pad","duration":4}' \
  -o /tmp/musicgen-test.wav
file /tmp/musicgen-test.wav   # expect: RIFF (little-endian) data, WAVE audio
```

If the AIO-GPU-HIPBLAS image still doesn't bundle musicgen on prod, fall
back to manually installing the python-musicgen backend per LocalAI's
custom-backend docs (option 2 above) and revisit the endpoint shape.

The deck-agent worker treats any non-2xx from `/v1/sound-generation` as a
generation failure (calls `set_generate_failed` with the response body),
so a missing backend on prod surfaces as a clear job-failure error rather
than a silent hang.

### Local stub for worker dev / CI

Until LocalAI is fully wired, a tiny Python HTTP stub on `127.0.0.1:8080`
returning a fake WAV body is enough to exercise the worker end-to-end:

```bash
python3 -c "
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type','audio/wav')
        self.end_headers()
        self.wfile.write(b'RIFF\x00\x00\x00\x00WAVE')
HTTPServer(('127.0.0.1', 8080), H).serve_forever()
"
```

Vitest specs in `workers/src/agents/deck-agent.test.ts` cover this path
without standing up the stub.

## Run locally

```bash
cd infra
mkdir -p localai/models
cp localai/models.yaml localai/models/models.yaml   # one-time, on each host
docker compose up -d localai
docker compose logs -f localai      # readyz at :8080/readyz once healthy
./localai/preload.sh                # POSTs /models/apply
curl http://127.0.0.1:8080/v1/models
```

The `cp` step exists because Docker can't bind-mount a single file inside a
directory we're already bind-mounting — see the `localai` block in
`docker-compose.yml`.

## Smoke test

```bash
# Test the wiring (will return 400 until a musicgen-capable image is in use):
curl -fsSL -X POST http://127.0.0.1:8080/v1/sound-generation \
  -H 'Content-Type: application/json' \
  -d '{"model":"musicgen-small","input":"calm ambient pad","duration":4}' \
  -o /tmp/musicgen-test.wav
file /tmp/musicgen-test.wav
```

When a musicgen-capable backend is installed, the response is a RIFF WAV.
On dev CPU, expect ~30 s for a 4-second clip; on prod GPU, sub-second.
