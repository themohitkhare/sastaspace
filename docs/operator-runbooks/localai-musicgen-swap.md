# Operator runbook — LocalAI audio backend on taxila

**Purpose:** keep `https://sastaspace.com/lab/deck` producing real audio bundles.

**Status as of 2026-04-27:** Audio generation **works** via piper TTS at `/v1/audio/speech`. The compose file now ships the AIO-GPU-HipBLAS image + ROCm device mounts as the default. This runbook documents what was done and what remains for **real music generation** (vs spoken narration).

## Current state

| Layer | Status |
|---|---|
| LocalAI image | `localai/localai:latest-aio-gpu-hipblas` (AMD ROCm) |
| Audio endpoint | `POST /v1/audio/speech` — piper TTS, 16-bit mono 16 kHz WAV |
| deck-agent target | `LOCALAI_AUDIO_PATH=/v1/audio/speech`, `LOCALAI_AUDIO_MODEL=tts-1`, voice=`en-us-amy-low` |
| Music generation (MusicGen / ACE-Step) | **broken** — see Known issues below |

The deck UI/agent flow produces narrated WAVs from track prompts. Bundles zip + serve at `https://deck.sastaspace.com/<job-id>.zip`.

## What was done (2026-04-27 cutover)

```bash
ssh mkhare@192.168.0.37

# 1. Pull AIO-GPU image (~14.5 GB on disk).
docker pull localai/localai:latest-aio-gpu-hipblas

# 2. compose was already patched in repo (image + devices + group_add for
#    video/render groups). Just bring it up.
cd /home/mkhare/sastaspace/infra
docker compose up -d --no-deps localai

# 3. Wait for /readyz (initial backend pull is ~10 min for rocm-llama-cpp).
until curl -sS -m 3 http://127.0.0.1:8080/readyz; do sleep 10; done

# 4. Smoke-test piper TTS (the path deck-agent uses today).
curl -sS -X POST http://127.0.0.1:8080/v1/audio/speech \
  -H 'Content-Type: application/json' \
  --data '{"model":"tts-1","input":"hello deck","voice":"en-us-amy-low"}' \
  -o /tmp/tts.wav
file /tmp/tts.wav  # → RIFF (little-endian) data, WAVE audio, ...
```

## Workers configuration

The workers `.env` on prod must contain the **owner JWT** for `STDB_TOKEN` — non-owner identities are rejected by `set_plan` / `set_generate_done`. The owner JWT is in `/home/mkhare/.config/spacetime/cli.toml`:

```bash
OWNER_TOK=$(grep ^spacetimedb_token /home/mkhare/.config/spacetime/cli.toml | sed 's/.*"\(.*\)"/\1/')
sed -i "s|^STDB_TOKEN=.*|STDB_TOKEN=$OWNER_TOK|" /home/mkhare/sastaspace/workers/.env
docker compose up -d --no-deps --force-recreate workers
```

## Known issues (real music generation)

**MusicGen / ACE-Step are not currently wired.** Both fail in LocalAI v3.12.1 + ROCm:

- **MusicGen via `/v1/sound-generation` + transformers backend:** PyTorch error `can't convert cuda:0 device type tensor to numpy. Use Tensor.cpu() to copy the tensor to host memory first.` Upstream bug.
- **ACE-Step via rocm-ace-step backend:** `rpc error: Exception calling application: GetCaption`. The two-stage pipeline (LM caption → DiT audio) crashes in the LM step on ROCm regardless of `init_lm` / `lyrics` configs.
- LocalAI v3.x dropped the dedicated `musicgen` backend that the original deck-agent code targeted; MusicGen now routes through generic transformers and inherits the cuda→numpy bug.

To pursue real music when one of those upstream fixes lands:

1. Install backend on prod LocalAI: `curl -X POST http://127.0.0.1:8080/backends/apply -H 'Content-Type: application/json' --data '{"id":"localai@<rocm-transformers|rocm-ace-step>"}'`
2. Install model: `curl -X POST http://127.0.0.1:8080/models/apply -H 'Content-Type: application/json' --data '{"id":"localai@<model-gallery-name>","name":"<deck-uses-this-name>"}'`
3. Override deck-agent env in compose: `LOCALAI_AUDIO_PATH=/v1/sound-generation`, `LOCALAI_AUDIO_MODEL=<deck-uses-this-name>`. Drop the `voice` field by setting `LOCALAI_AUDIO_VOICE=`.
4. Rebuild + restart workers.

## Three other workers (auth-mailer / admin-collector / moderator) currently disabled

The compose flags `WORKER_AUTH_MAILER_ENABLED`, `WORKER_ADMIN_COLLECTOR_ENABLED`, `WORKER_MODERATOR_AGENT_ENABLED` are all `false`. Each crashes the workers process because:

- **auth-mailer** subscribes to `pending_email` table — accessor missing in the generated TS bindings (silently `undefined`, `.onInsert` throws TypeError).
- **admin-collector** subscribes to `log_interest` table — same root cause.
- **moderator-agent** boots fine but its owner-only `set_comment_status_with_reason` reducer call hits an uncaught SDK 2.1 SenderError that takes down the node process.

Real fix for the first two is `pnpm bindings:generate` against the deployed module (which has those tables) and rebuilding workers. Real fix for moderator is wrapping the SDK reducer call in a SenderError-aware handler. Both are tracked in the consolidated audit; until done these three stay `false`.
