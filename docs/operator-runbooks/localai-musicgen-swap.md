# Operator runbook — LocalAI MusicGen image swap

**Purpose:** make `https://sastaspace.com/lab/deck` actually produce real audio bundles instead of falling back to the offline-stub text file.

**Status:** **owner action required** — the swap has not been done. Until it lands, the deck UI shows "demo only — no audio (set NEXT_PUBLIC_DECK_API_URL or use STDB mode)" instead of "downloaded ✓" (audit-fix `84475ccc`).

**Why blocked:** the prod compose currently runs `localai/localai:latest` which is the **CPU-only** image with no MusicGen backend bundled. Every `/v1/sound-generation` call returns HTTP 400; the deck-agent worker then calls `set_generate_failed` and the UI falls through to the stub. To produce real audio we need the AIO-GPU-HipBLAS image (AMD GPU) with the appropriate device mounts.

## Pre-flight

1. Confirm the prod host (`taxila`, 192.168.0.37) has AMD GPU drivers + `/dev/kfd` and `/dev/dri` device nodes: `ls -la /dev/kfd /dev/dri`. ROCm 5.x or higher.
2. Stop and free disk: the AIO image is ~16 GB. `df -h /var/lib/docker` should show ≥30 GB free.
3. Snapshot current LocalAI logs and any in-flight `generate_job` rows (none expected since current image returns 400 anyway, but verify).

## Step 1 — pull the AIO-GPU image on prod

```bash
ssh mkhare@192.168.0.37
docker pull localai/localai:latest-aio-gpu-hipblas
```

This pull is large; expect 5–15 min depending on bandwidth.

## Step 2 — update compose to swap the image + add GPU device mounts

Edit `/home/mkhare/sastaspace/infra/docker-compose.yml`. Find the `localai:` service block. Change:

```yaml
  localai:
    image: localai/localai:latest          # ← change to:
    image: localai/localai:latest-aio-gpu-hipblas
```

Add device + group mounts under the same service:

```yaml
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
      - render
```

Optionally pin a specific MusicGen model in the model list (LocalAI auto-detects by filename in `/build/models/` — copy the .bin or .safetensors there if you want a specific quality tier; the default AIO image bundles `musicgen-medium`).

## Step 3 — restart the service

```bash
cd /home/mkhare/sastaspace/infra
docker compose up -d localai
sleep 30
docker logs sastaspace-localai --tail 50
```

Watch for `model loaded: musicgen-*` and no GPU initialization errors. First-run model load can take 2–3 min.

## Step 4 — smoke test from the host

```bash
curl -sS http://127.0.0.1:8080/v1/sound-generation \
  -H "Content-Type: application/json" \
  -d '{"model":"musicgen-medium","input":"warm pad","duration":4}' \
  --output /tmp/musicgen-smoke.wav
file /tmp/musicgen-smoke.wav  # expect: RIFF (little-endian) data, WAVE audio
```

If the file is non-empty WAV (>20 KB) the smoke is green.

## Step 5 — verify the prod flow end-to-end

1. Visit `https://sastaspace.com/lab/deck` in a browser.
2. Brief: any 1-2 sentence description (e.g. "calm meditation app").
3. Click "Generate". Wait through plan + render (the render step is what was previously failing).
4. Click the download link. Confirm the downloaded `.zip` contains real `.wav` files (not a `.txt` stub).
5. Visit `https://deck.sastaspace.com/<job-id>.zip` directly to confirm nginx serves the produced bundle.

## Step 6 — update Deck.tsx to drop the misleading-stub workaround

Once production deck audio is verified end-to-end, the `if (!API_URL)` branch in `apps/landing/src/app/lab/deck/Deck.tsx:905-913` (the "demo only" fallback) becomes dead code for the prod build. Either:
- Set `NEXT_PUBLIC_DECK_API_URL` in the landing's CI build env so the legacy path always uses the real LocalAI, OR
- Remove the legacy path entirely and require `NEXT_PUBLIC_USE_STDB_DECK=true` (already the prod build default).

## Rollback

If the AIO image misbehaves or eats too much GPU/VRAM:

```bash
docker compose stop localai
sed -i 's|localai/localai:latest-aio-gpu-hipblas|localai/localai:latest|' /home/mkhare/sastaspace/infra/docker-compose.yml
# Remove the devices: + group_add: blocks added above.
docker compose up -d localai
```

This restores the CPU image; deck audio goes back to "demo only" but other apps are unaffected.

## Tracked in

- Audit: `docs/audits/2026-04-26-audit-feature-readiness.md` Critical #1
- Loop directive: operator-only blocker (P3) — autonomous loop cannot perform this remotely.
