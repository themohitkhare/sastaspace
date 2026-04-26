#!/usr/bin/env bash
# Preloads the MusicGen model on first boot. Run inside the LocalAI container
# via an init job in docker-compose, OR run manually after first up.
set -euo pipefail
LOCALAI_URL="${LOCALAI_URL:-http://127.0.0.1:8080}"
echo "Preloading musicgen-small via $LOCALAI_URL ..."
curl -fsSL -X POST "$LOCALAI_URL/models/apply" \
  -H 'Content-Type: application/json' \
  -d '{"id":"musicgen-small","name":"musicgen-small","backend":"musicgen","parameters":{"model":"facebook/musicgen-small"}}' \
  | tee /tmp/localai-preload.json
echo "OK"
