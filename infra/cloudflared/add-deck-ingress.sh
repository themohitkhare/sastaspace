#!/usr/bin/env bash
# Add `deck.sastaspace.com` to the existing sastaspace-prod tunnel.
# Run on a machine that has the keychain entry for cloudflare-api-token.
#
# Idempotent: skips if the hostname is already in the ingress list.
#
# Routes deck.sastaspace.com → http://localhost:3160, where the
# `deck-static` nginx container (infra/docker-compose.yml, profile
# `stdb-native`) serves zips written by workers/src/agents/deck-agent.ts.

set -euo pipefail

CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
ZONE=f90dcc0f12180c1d2b5fb5d488887c24
ACCOUNT=c207f71f99a2484494c84d95e6cb7178
TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8
NAME=deck
HOSTNAME=$NAME.sastaspace.com
SERVICE=http://localhost:3160

# 1. CNAME record (idempotent — Cloudflare returns 81057 if it already exists)
curl -sS -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  --data "{\"type\":\"CNAME\",\"name\":\"$NAME\",\"content\":\"$TUNNEL.cfargotunnel.com\",\"proxied\":true}" \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('dns:', 'ok' if r.get('success') else r.get('errors'))"

# 2. Tunnel ingress rule (insert before the catch-all)
CFG=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
       -H "Authorization: Bearer $CF_TOKEN")
echo "$CFG" | HOSTNAME="$HOSTNAME" SERVICE="$SERVICE" python3 -c '
import json, os, sys
d = json.load(sys.stdin); cfg = d["result"]["config"]; ing = cfg["ingress"]
host = os.environ["HOSTNAME"]; svc = os.environ["SERVICE"]
if any(r.get("hostname") == host for r in ing):
    print("ingress: already present")
    sys.exit(0)
idx = next(i for i, r in enumerate(ing) if "hostname" not in r)
ing.insert(idx, {"hostname": host, "service": svc})
json.dump({"config": cfg}, open("/tmp/cfg-deck.json", "w"))
print("ingress: prepared", host, "->", svc)
'

if [[ -f /tmp/cfg-deck.json ]]; then
  curl -sS -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
    -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/cfg-deck.json \
    | python3 -c "import json,sys; r=json.load(sys.stdin); print('tunnel:', 'ok' if r.get('success') else r.get('errors'))"
  rm /tmp/cfg-deck.json
fi
