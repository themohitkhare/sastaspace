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
1. Switch to a LocalAI image variant that bundles musicgen (the AIO-GPU images
   bundle more backends — verify on prod with `docker exec sastaspace-localai
   ls /build/backend/python/`).
2. Manually install the musicgen backend into the `models/` dir per LocalAI's
   custom-backend docs.
3. Use a different audio model that IS in the v4.1.3 default gallery
   (`parler-tts-mini-v0.1` is a TTS model — would change the deck-agent UX).

Phase 0's goal is to prove the deployment path; Phase 1 W3 picks a concrete
musicgen install strategy.

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
