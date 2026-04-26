#!/usr/bin/env bash
# Verifies that api.sastaspace.com is NOT in the active cloudflared tunnel
# ingress config. Exits 0 if absent (the desired post-cutover state),
# non-zero if still present.
#
# Run after Phase 3 Task B5 and as part of the Phase 3 acceptance gate.
# Implements audit finding N22.

set -euo pipefail

CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w 2>/dev/null || echo "${CF_API_TOKEN:-}")
[[ -z "$CF_TOKEN" ]] && { echo "::error::no cloudflare token (keychain or CF_API_TOKEN env)"; exit 2; }
ACCOUNT=c207f71f99a2484494c84d95e6cb7178
TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8

CFG=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
       -H "Authorization: Bearer $CF_TOKEN")

HOSTS=$(echo "$CFG" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for r in d["result"]["config"]["ingress"]:
    if "hostname" in r:
        print(r["hostname"])
')

echo "tunnel hostnames currently routed:"
echo "$HOSTS" | sed "s/^/  /"

if echo "$HOSTS" | grep -qx "api.sastaspace.com"; then
  echo "::error::api.sastaspace.com is STILL in the cloudflared tunnel ingress."
  exit 1
fi
echo "ok: api.sastaspace.com absent from cloudflared ingress"
