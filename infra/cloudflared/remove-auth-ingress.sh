#!/usr/bin/env bash
# Remove `auth.sastaspace.com` from the existing sastaspace-prod tunnel.
# Run on a machine that has the keychain entry for cloudflare-api-token.
#
# Idempotent: succeeds silently if the hostname is not in the ingress list.
#
# Inverse of cloudflared/add-stdb-ingress.sh shape — drops the tunnel rule
# and (optionally) deletes the orange-cloud DNS record. The DNS record is
# left in place by default so requests continue to be routed to Cloudflare
# (they 1014/Argo-error rather than NXDOMAIN). Pass --drop-dns to remove
# the CNAME too.
#
# Phase 4 of the SpacetimeDB-native rewire runs this ≥7 days after Phase 3
# cutover. Until then, the auth-410 nginx container (compose profile
# `stdb-native`) serves a 410 Gone tombstone at the same hostname.

set -euo pipefail

DROP_DNS=0
for arg in "$@"; do
  case "$arg" in
    --drop-dns) DROP_DNS=1 ;;
    -h|--help)
      echo "Usage: $0 [--drop-dns]"
      echo "  --drop-dns   Also delete the auth.sastaspace.com CNAME record."
      exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
ZONE=f90dcc0f12180c1d2b5fb5d488887c24
ACCOUNT=c207f71f99a2484494c84d95e6cb7178
TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8
NAME=auth
HOSTNAME=$NAME.sastaspace.com

# 1. Tunnel ingress rule removal
CFG=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
       -H "Authorization: Bearer $CF_TOKEN")
echo "$CFG" | HOSTNAME="$HOSTNAME" python3 -c '
import json, os, sys
d = json.load(sys.stdin); cfg = d["result"]["config"]; ing = cfg["ingress"]
host = os.environ["HOSTNAME"]
before = len(ing)
cfg["ingress"] = [r for r in ing if r.get("hostname") != host]
after = len(cfg["ingress"])
if before == after:
    print("ingress: nothing to remove (", host, "not present)")
    sys.exit(0)
json.dump({"config": cfg}, open("/tmp/cfg-remove-auth.json", "w"))
print("ingress: prepared removal of", host, "(", before, "->", after, "rules)")
'

if [[ -f /tmp/cfg-remove-auth.json ]]; then
  curl -sS -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
    -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
    --data @/tmp/cfg-remove-auth.json \
    | python3 -c "import json,sys; r=json.load(sys.stdin); print('tunnel:', 'ok' if r.get('success') else r.get('errors'))"
  rm /tmp/cfg-remove-auth.json
fi

# 2. (Optional) DNS record removal
if [[ $DROP_DNS -eq 1 ]]; then
  REC=$(curl -sS "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?name=$HOSTNAME" \
         -H "Authorization: Bearer $CF_TOKEN")
  REC_ID=$(echo "$REC" | python3 -c "import json,sys; d=json.load(sys.stdin); rs=d.get('result',[]); print(rs[0]['id'] if rs else '')")
  if [[ -z "$REC_ID" ]]; then
    echo "dns: no $HOSTNAME record found"
  else
    curl -sS -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records/$REC_ID" \
      -H "Authorization: Bearer $CF_TOKEN" \
      | python3 -c "import json,sys; r=json.load(sys.stdin); print('dns:', 'ok' if r.get('success') else r.get('errors'))"
  fi
else
  echo "dns: kept (pass --drop-dns to delete the $HOSTNAME CNAME)"
fi
