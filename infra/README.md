# infra — sastaspace SpacetimeDB self-host

SpacetimeDB runs on the prod box, bound to `127.0.0.1:3100`, exposed publicly at
`https://stdb.sastaspace.com` via the existing `sastaspace-prod` Cloudflare tunnel.

## First-time setup

```bash
# on a workstation with keychain access
./cloudflared/add-stdb-ingress.sh        # adds stdb.sastaspace.com to the tunnel

# on the prod box
chmod +x keygen.sh
./keygen.sh                              # writes ./keys/id_ecdsa{,.pub}
docker compose up -d                     # starts spacetimedb on 127.0.0.1:3100
docker compose logs -f spacetime         # tail to confirm "listening on 0.0.0.0:3000"

# verify from outside (anywhere)
curl https://stdb.sastaspace.com/v1/identity   # should return 200 with a fresh identity
```

## Ports

| Where | Port | What |
|---|---|---|
| Container internal | `3000` | SpacetimeDB HTTP + WebSocket |
| Host loopback     | `3100` | Mapped from container; only Cloudflared reaches it |
| Public            | `443`  | `stdb.sastaspace.com` via tunnel |

## Volumes

- `stdb_data` (named volume) — module state, identities, transaction log. **Back this up.**
- `./keys` (bind mount, read-only) — JWT signing keypair. **Back this up too.** Losing it invalidates every issued identity.

## Updating SpacetimeDB

```bash
docker compose pull spacetime
docker compose up -d
```

## STDB-native cutover (Phase 3)

The compose file ships a `stdb-native` profile (currently: `deck-static`) for services
that replace the legacy Python services without colliding on host ports. Both old
and new can sit in the same file but only one set may run at a time.

```bash
# on a workstation with keychain access
./cloudflared/add-deck-ingress.sh                        # adds deck.sastaspace.com to the tunnel

# on the prod box (taxila), at cutover time
docker compose stop deck && docker compose rm -f deck    # legacy Python deck-API
docker compose --profile stdb-native up -d deck-static   # static nginx for workers' MusicGen zips
curl -I https://deck.sastaspace.com/                     # 200 (autoindex) — verifies tunnel + nginx
```

After Phase 3 cutover, `auth.sastaspace.com` continues to resolve but serves a
`410 Gone` page (see `landing/auth-410.conf` + the `auth-410` compose service).
Phase 4 — at least 7 days post-cutover — runs:

```bash
./cloudflared/remove-auth-ingress.sh                     # drops the auth.sastaspace.com tunnel rule
docker compose stop auth-410 && docker compose rm -f auth-410
```

## Adding a publish token for CI

```bash
# on a workstation logged in via the spacetime CLI
spacetime server add prod --url https://stdb.sastaspace.com
spacetime login --server-issued-login prod
spacetime token export --server prod    # paste the printed token into GH secret SPACETIME_TOKEN
```
