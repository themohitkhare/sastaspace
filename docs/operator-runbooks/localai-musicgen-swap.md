# Operator runbook — Audio backends on taxila

**Purpose:** keep `https://sastaspace.com/lab/deck` producing real music bundles.

**Status as of 2026-04-27 evening:** **Real music generation works** via ACE-Step 1.5 at `http://127.0.0.1:8001`. Output is 48 kHz stereo, ~1-2 minutes per ~15-second track on the RX 7900 XTX. The deck-agent's compose default is `DECK_AUDIO_BACKEND=acestep`. Piper TTS at LocalAI's `/v1/audio/speech` remains the fallback (set the env back to `tts`).

## Architecture

```
[deck-agent in workers container, network_mode: host]
   │
   ├──→ http://127.0.0.1:8001  (ACE-Step 1.5 API — host process, GPU)
   │       └─ /release_task → /query_result → /v1/audio?path=...
   │
   └──→ http://127.0.0.1:8080  (LocalAI AIO-GPU — Docker, GPU)
           └─ /v1/audio/speech (piper TTS, fallback)
```

ACE-Step and LocalAI **cannot run simultaneously on the GPU** — both need most of the 24 GB VRAM. The compose `localai` service is currently stopped; bring it back only when you intend to fall back to TTS (or after upgrading to a GPU with more memory).

## ACE-Step 1.5 setup (one-shot, already done 2026-04-27)

```bash
ssh mkhare@192.168.0.37
cd /home/mkhare
git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git acestep
cd acestep
python3 -m venv venv_rocm
source venv_rocm/bin/activate
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3
pip install -r requirements-rocm-linux.txt
pip install -e acestep/third_parts/nano-vllm --no-deps
pip install -e . --no-deps
# Fix HF cache perms (was root-owned from a prior LocalAI run):
sudo chown -R mkhare:mkhare /home/mkhare/.cache/huggingface
```

## Run the API server

```bash
cd /home/mkhare/acestep
HSA_OVERRIDE_GFX_VERSION=11.0.0 \
ACESTEP_LM_BACKEND=pt \
MIOPEN_FIND_MODE=FAST \
TOKENIZERS_PARALLELISM=false \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
nohup ./venv_rocm/bin/acestep-api \
  --host 127.0.0.1 --port 8001 \
  --download-source huggingface \
  --lm-model-path acestep-5Hz-lm-0.6B \
  > /home/mkhare/acestep-logs/server.log 2>&1 < /dev/null &
```

Required env:
- `HSA_OVERRIDE_GFX_VERSION=11.0.0` — gfx1100 magic env var for RX 7900 XTX
- `ACESTEP_LM_BACKEND=pt` — bypass nano-vllm flash_attn dependency
- `MIOPEN_FIND_MODE=FAST` — without this VAE decode hangs on each conv layer
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` — defragments the heap
- `--lm-model-path acestep-5Hz-lm-0.6B` — smaller LM (default 1.7B blew past VRAM next to LocalAI)

First request will download ~10-15 GB of models from HuggingFace. Persist across reboots by promoting this to a systemd unit (TODO — not done yet).

## Verify

```bash
# Health
curl -sS http://127.0.0.1:8001/health

# Submit a task
curl -sS -X POST http://127.0.0.1:8001/release_task \
  -H 'Content-Type: application/json' \
  --data '{"prompt":"calm focused workspace ambient pad","audio_duration":15,"audio_format":"wav","inference_steps":8,"thinking":false,"sample_mode":false,"use_cot_caption":false,"use_cot_language":false,"batch_size":1}'
# → returns {"data":{"task_id":"<uuid>", ...}}

# Poll
curl -sS -X POST http://127.0.0.1:8001/query_result \
  -H 'Content-Type: application/json' \
  --data '{"task_id_list":["<uuid>"]}'
# → status:1 (success), result.file = "/v1/audio?path=..."

# Download
curl -sS 'http://127.0.0.1:8001/v1/audio?path=...' -o out.wav
file out.wav
# → RIFF, WAVE audio, Microsoft PCM, 16 bit, stereo 48000 Hz
```

## Workers configuration

The workers `.env` on prod must contain the **owner JWT** for `STDB_TOKEN`:

```bash
OWNER_TOK=$(grep ^spacetimedb_token /home/mkhare/.config/spacetime/cli.toml | sed 's/.*"\(.*\)"/\1/')
sed -i "s|^STDB_TOKEN=.*|STDB_TOKEN=$OWNER_TOK|" /home/mkhare/sastaspace/workers/.env
```

The compose file ships `DECK_AUDIO_BACKEND=acestep` and `ACESTEP_URL=http://127.0.0.1:8001` as defaults. To switch to TTS fallback, override either in `workers/.env`.

## Falling back to TTS (LocalAI piper)

If ACE-Step is down for any reason:

```bash
# Stop ACE-Step (frees VRAM)
pkill -f acestep-api

# Bring LocalAI back up (it's currently stopped because of GPU contention)
cd /home/mkhare/sastaspace/infra
docker compose up -d localai

# Switch deck-agent backend
echo 'DECK_AUDIO_BACKEND=tts' >> /home/mkhare/sastaspace/workers/.env
docker compose up -d --force-recreate workers
```

## Known issues we tried and ruled out

- **LocalAI v3 `transformers` backend + facebook/musicgen-small:** `TypeError: can't convert cuda:0 device type tensor to numpy. Use Tensor.cpu() to copy the tensor to host memory first.` — bug in LocalAI's wrapper, not the model. (Untracked upstream as of 2026-04-27.)
- **LocalAI v3 `rocm-ace-step` backend:** `rpc error: Exception calling application: GetCaption`. Crashes regardless of `init_lm`/`lyrics` flags. The model itself works fine outside the LocalAI wrapper (this runbook proves that).

## Three other workers (auth-mailer / admin-collector / moderator) currently disabled

The compose flags `WORKER_AUTH_MAILER_ENABLED`, `WORKER_ADMIN_COLLECTOR_ENABLED`, `WORKER_MODERATOR_AGENT_ENABLED` are all `false`. Each crashes the workers process because:

- **auth-mailer** subscribes to `pending_email` table — accessor missing in the generated TS bindings.
- **admin-collector** subscribes to `log_interest` table — same root cause.
- **moderator-agent** boots fine but its owner-only `set_comment_status_with_reason` reducer call hits an uncaught SDK 2.1 SenderError that takes down the node process.

Real fix for the first two is `pnpm bindings:generate` against the deployed module (which has those tables) and rebuilding workers. Real fix for moderator is wrapping the SDK reducer call in a SenderError-aware handler. Both are tracked in the consolidated audit.
