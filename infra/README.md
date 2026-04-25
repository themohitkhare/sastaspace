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

## Adding a publish token for CI

```bash
# on a workstation logged in via the spacetime CLI
spacetime server add prod --url https://stdb.sastaspace.com
spacetime login --server-issued-login prod
spacetime token export --server prod    # paste the printed token into GH secret SPACETIME_TOKEN
```
